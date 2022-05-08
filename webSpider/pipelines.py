# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import os
from time import strftime
import uuid
import logging


class ElasticSearchPipeline:
    def __init__(self):
        self.es = {}
        self.es_connected = True

    def open_spider(self, spider):
        load_dotenv()
        logging.debug("print config value: %s", os.environ)

        USERNAME = os.environ.get("USERNAME", False)
        PASSWORD = os.environ.get("PASSWORD", False)
        ES_URL = os.environ.get("ES_URL", False)
        CERT = os.environ.get("CERT", False)

        if not (USERNAME and PASSWORD and URL and CERT):
            self.es_connected = False
        else:
            # 详情参考官方文档
            # https://www.elastic.co/guide/en/elasticsearch/client/python-api/8.2/connecting.html
            # Or
            # https://elasticsearch-py.readthedocs.io/en/v8.2.0/
            try:
                # Create the client instance

                self.es = Elasticsearch(
                    ES_URL,
                    ca_certs=CERT,
                    basic_auth=(USERNAME, PASSWORD),
                )
                logging.debug("ElasticSearch Connected")

                INDEX = os.environ.get("ES_INDEX", "policy")

                self.es.search(index=INDEX, filter_path=["hits.total.value"])
            except Exception:
                logging.exception("Fail to connect ElasticSearch.")
                self.es_connected = False

    def close_spider(self, spider):
        pass

    def process_item(self, item, spider):

        if self.es_connected:

            logging.debug("Processing items in pipelines: {}".format(item))

            index = os.environ["ES_INDEX"]

            logging.debug("publishingDate: " + item["publishingDate"])

            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "term": {
                                    "urlSource.keyword": {"value": item["urlSource"]}
                                }
                            },
                        ]
                    }
                }
            }

            insert_body = ItemAdapter(item).asdict()
            insert_body["@timestamp"] = strftime("%Y-%m-%dT%H:%M:%S%z")

            result = self.es.search(
                index=index,
                body=search_body,
                filter_path=["hits.hits._id", "hits.total.value"],
            )

            id = ""
            count = result["hits"]["total"]["value"]

            if count == 0:
                self.es.create(index=index, body=insert_body, id=uuid.uuid1())
            else:
                id = result["hits"]["hits"][0]["_id"]
                self.es.update(index=index, id=id, body={"doc": insert_body})

        return item
