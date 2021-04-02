# -*- coding: utf-8 -*-
import scrapy
from scrapy.linkextractors import LinkExtractor
from datetime import date
# from scrapy.spiders import CrawlSpider, Rule

import re, string

class PlayerSpider(scrapy.Spider):
    name = 'player'
    allowed_domains = ['basketball-reference.com']
    start_urls = []

    def __init__(self, **kwargs):
        '''
        Expects seasons and months.
        '''
        self.ids = []
        if 'ids' in kwargs:
            self.ids = [x for x in kwargs['ids'].split(',')]
        else:
            self.ids = []

        # Starts with letter l
        if 'l' in kwargs:
            self.letters = [x for x in kwargs['l'].split(',')]
        elif 'all' in kwargs:
            self.letters = list(string.ascii_lowercase) # the alphabet
        else:
            self.letters = []

        

    def start_requests(self):
        '''
        Initial requests that will be processed, based on the arguments passed.
        '''
        # Example: https://www.basketball-reference.com/players/h/hardeja01.html

        PLAYER_URL = 'https://www.basketball-reference.com/players/{}/{}.html'
        for id in self.ids:
            url = PLAYER_URL.format(id[0], id)
            yield scrapy.Request(url, callback=self.parse_player)

        LIST_URL = 'https://www.basketball-reference.com/players/{}'
        for letter in self.letters:
            url = LIST_URL.format(letter)
            yield scrapy.Request(url, callback=self.parse_list)


    def parse_list(self, response):
        '''
        Extracts information about the 
        '''
        for a in response.xpath('//a/@href'):
            url = a.extract()
            if re.match(r'/players/[a-z]/([a-z]){7}(\d){2}\.html', url):
                yield response.follow(url, callback=self.parse_player)
                pass

        list_entries = []
        players_xpath = '//table[@id="players"]//tbody//tr[not(contains(@class, "thead"))]'
        players = response.xpath(players_xpath)
        for player in players:
            
            entry = self.get_list_entry()

            stats = player.xpath('th | td')
            for stat in stats:
                dt_st = stat.attrib['data-stat']

                if stat.xpath('.//a'):   # if it has link...
                    if dt_st == 'colleges':
                        entry[dt_st] = stat.get()
                    else:
                        entry[dt_st] = stat.xpath('.//a/text()').get()
                        entry['{}_href'.format(dt_st)] = stat.xpath('.//a/@href').get()
                else:
                    entry[dt_st] = stat.xpath('text()').get()

                if 'csk' in stat.attrib:
                    entry['{}_csk'.format(dt_st)] = stat.attrib['csk']

                if 'data-append-csv' in stat.attrib:
                    entry['{}_data-append-csv'.format(dt_st)] = stat.attrib['data-append-csv']

            pass # end stats for

            list_entries.append(entry)
            
        if list_entries:
            yield { 'file_name': response.url.rstrip('/')[-1], 
                    'type': 'player_list', 
                    'dir': 'players/list', 
                    'data': list_entries,
                    'fieldnames': self.get_list_keys() }
        pass # end player for
        


            
    def parse_player(self, response):
        player_id = re.search(r"/([a-z\d]*)?.html", response.url).group(1)

        player_data = {}

        # Tables are commented: need to remove HTML comments.
        html_body = response.xpath('//body').get()
        html_body_uncommented = html_body.replace("<!--", "").replace("-->", "")
        selector = scrapy.selector.Selector(text=html_body_uncommented)
        data_tables = selector.xpath('//table[contains(@class, "stats_table")]')

        for data_table in data_tables:
            table_id = data_table.attrib['id']

            player_data[table_id] = []

            data_rows = data_table.xpath('tbody//tr[not(contains(@class, "thead"))]')
            for data_row in data_rows:

                entry = {
                    "player_id": player_id,
                    "table_id": table_id,
                }
                
                stats = data_row.xpath('th | td')
                for stat in stats:
                    try:
                        dt_st = stat.attrib['data-stat']

                        if stat.xpath('a'):   # if it has link...
                            entry[dt_st] = stat.xpath('.//a/text()').get()
                            entry['{}_href'.format(dt_st)] = stat.xpath('.//a/@href').get()
                        else:
                            entry[dt_st] = stat.xpath('text()').get()

                        if 'csk' in stat.attrib:
                            entry['{}_csk'.format(dt_st)] = stat.attrib['csk']

                        if 'data-append-csv' in stat.attrib:
                            entry['{}_data_append_csv'.format(dt_st)] = stat.attrib['data-append-csv']
                    except KeyError:
                        pass
                        

                player_data[table_id].append(entry)
            pass # end player for
        
        if player_data:
            yield { 'file_name': player_id, 
                    'type': 'player', 
                    'dir': 'players/data/{}'.format(player_id[0]), 
                    'data': player_data, 
                    'fieldnames': None }

    
    def get_list_keys(self):
        keys = [
            "player",
            "player_href",
            "player_id",
            "year_min",
            "year_max",
            "pos",
            "weight",
            "height",
            "height_csk",
            "birth_date",
            "birth_date_csk",
            "colleges"
        ]
        return keys

    def get_list_entry(self):
        entry = {}
        keys = self.get_list_keys()

        for key in keys:
            entry[key] = None

        return entry

    def get_stats_keys(self):
        keys = [
            "player_id",
            "stat_type",
            "isplayoff",
            "season",
            "season_href",
            "age",
            "team_id",
            "team_id_href",
            "lg_id",
            "lg_id_href",
            "pos",
            "g",
            "gs",
            "mp",
            "fg",
            "fga",
            "fg_pct",
            "fg3",
            "fg3a",
            "fg3_pct",
            "fg2",
            "fg2a",
            "fg2_pct",
            "ft",
            "fta",
            "ft_pct",
            "orb",
            "drb",
            "trb",
            "ast",
            "stl",
            "blk",
            "tov",
            "pf",
            "pts"
        ]
        return keys
                
    def get_stats_entry(self):
        entry = {}
        keys = self.get_stats_keys()
        for key in keys:
            entry[key] = None
        return entry



    def get_advanced_keys(self):
        keys = ["game_id", 
            "team_id", 
            "box_type", 
            "date",  
            "ishome", 
            "pnum", 
            "player", 
            "player_href", 
            "player_csk", 
            "player_id", 
            "mp",
            "sp",
            "ts_pct", 
            "efg_pct", 
            "fg3a_per_fga_pct", 
            "fta_per_fga_pct", 
            "orb_pct", 
            "drb_pct", 
            "trb_pct", 
            "ast_pct", 
            "stl_pct", 
            "blk_pct", 
            "tov_pct", 
            "usg_pct", 
            "off_rtg", 
            "def_rtg", 
            "bpm", 
            "reason"]
        return keys    


    def get_advanced_entry(self):
        entry = {}
        keys = self.get_advanced_keys()
        for key in keys:
            if key in ['sp', 'mp']:
                entry[key] = 0
            else:
                entry[key] = None
        return entry