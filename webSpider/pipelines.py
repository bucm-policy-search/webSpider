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

    def connect_elasticsearch(self):
        load_dotenv()
        logging.debug("print config value: %s", os.environ)

        username = os.environ["USERNAME"]
        PASSWORD = os.environ["PASSWORD"]
        URL = os.environ["URL"]

        # 详情参考官方文档 https://elasticsearch-py.readthedocs.io/en/7.x/
        try:
            self.es = Elasticsearch(
                ["http://{}:{}@{}/".format(username, PASSWORD, URL)]
            )
            logging.debug("ElasticSearch connected")
            self.es.search(index="policy", filter_path=["hits.hits._id"])
        except Exception:
            logging.error("Fail to connect ElasticSearch.")
            self.es_connected = False

    def open_spider(self, spider):
        self.connect_elasticsearch()

    def close_spider(self, spider):
        pass

    def process_item(self, item, spider):

        if self.es_connected:

            logging.debug("Processing items in pipelines: {}".format(item))

            index = "policy"

            logging.debug("publishingDate: " + item["publishingDate"])

            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"title.keyword": {"value": item["title"]}}},
                            {"match": {"publishingDate": item["publishingDate"]}},
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

            if self.es.count(index=index, body=search_body)["count"] == 0:
                self.es.create(index=index, body=insert_body, id=uuid.uuid1())

        return item