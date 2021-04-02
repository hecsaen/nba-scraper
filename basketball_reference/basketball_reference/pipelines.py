# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import os
import csv, json
from scrapy.utils.project import get_project_settings
# usage: https://stackoverflow.com/questions/14075941/how-to-access-scrapy-settings-from-item-pipeline
# > settings = get_project_settings()
# > settings.get('USER_AGENT')

class BasketballReferencePipeline:
    def process_item(self, item, spider):
        if item['type'] in ['boxscore', 'player_list', 'schedule', 'shot']:
            self.store_item_csv(item, spider)

        if item['type'] in ['player']:
            self.store_item_json(item, spider)
        return None

    
    def store_item_csv(self, item, spider):
        settings = get_project_settings()
        output_dir = settings.get('OUTPUT_DIR')

        dir_path = '{}/{}'.format(output_dir, item['dir'])
        os.makedirs(dir_path, exist_ok=True)

        file_name = '{}/{}.csv'.format(dir_path, item['file_name'])

        try:
            f = open(file_name, mode='w', encoding='utf-8', newline='\n')
            writer = csv.DictWriter(f, fieldnames=item['fieldnames'], 
                                    extrasaction='ignore', lineterminator='\n')
            writer.writeheader()
            for entry in item['data']:  
                writer.writerow(entry)
            f.close()
        except:
            spider.logger.error("Error writing to {}.".format(file_name))



    def store_item_json(self, item, spider):
        settings = get_project_settings()
        output_dir = settings.get('OUTPUT_DIR')

        dir_path = '{}/{}'.format(output_dir, item['dir'])
        os.makedirs(dir_path, exist_ok=True)

        file_name = '{}/{}.json'.format(dir_path, item['file_name'])

        try:
            f = open(file_name, mode='w', encoding='utf-8', newline='\n')
            json.dump(item['data'], f, ensure_ascii=False)
            f.close()
        except:
            spider.logger.error("Error writing to {}.".format(file_name))
            
