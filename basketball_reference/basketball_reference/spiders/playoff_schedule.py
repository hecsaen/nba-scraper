# -*- coding: utf-8 -*-
import scrapy
from scrapy.linkextractors import LinkExtractor
from datetime import date
# from scrapy.spiders import CrawlSpider, Rule

import re

class BoxscoresSpider(scrapy.Spider):
    name = 'playoff_schedule'
    allowed_domains = ['basketball-reference.com']
    start_urls = []

    def __init__(self, **kwargs):
        '''
        Expects seasons and months.
        '''
        if 'seasons' in kwargs:
            self.seasons = [int(x) for x in kwargs['seasons'].split(',')]
        else:
            self.seasons = ()

        if 'from_season' and 'to_season' in kwargs:
            from_season = int(kwargs['from_season'])
            to_season = int(kwargs['to_season'])

            self.seasons = [x for x in range(from_season, to_season + 1)]

        if 'date' in kwargs:
            if kwargs['date'] == 'today' or kwargs['date'] == 'season':
                self.seasons = [date.today().year - 1, date.today().year, date.today().year + 1]


    def start_requests(self):
        '''
        Initial requests that will be processed, based on the arguments passed.
        '''
        BASE_URL = 'https://www.basketball-reference.com'
        SCHEDULE_URL = '/playoffs/NBA_{season}_games.html'

        for season in self.seasons:
            url = BASE_URL + SCHEDULE_URL.format(season=season)
            yield scrapy.Request(url, callback=self.parse_schedule)


    def parse_schedule(self, response):
        '''
        Extracts information about the 
        '''
        games_xpath = '//table[@id="schedule"]//tbody//tr[not(contains(@class, "thead"))]'
        games = response.xpath(games_xpath)

        season = re.search(r"/NBA_([0-9]{4})?_games.html", response.url).group(1)

        entries = []
        for game in games:
            entry = self.get_game_entry()

            entry["game_id"] = game.xpath('.//*[@data-stat="date_game"]//@csk').get()
            
            game_id = entry["game_id"] 
            y, m, d = int(game_id[0:4]), int(game_id[4:6]), int(game_id[6:8])
            entry["date"] = date(y, m, d).isoformat()

            entry["start_time"] = game.xpath('.//*[@data-stat="game_start_time"]//text()').get()
            entry["visitor_team"] = game.xpath('.//*[@data-stat="visitor_team_name"]//text()').get()
            entry["visitor_team_id"] = game.xpath('.//*[@data-stat="visitor_team_name"]//@csk').get()[:3]
            entry["visitor_pts"] = game.xpath('.//*[@data-stat="visitor_pts"]//text()').get()
            entry["home_team"] = game.xpath('.//*[@data-stat="home_team_name"]//text()').get()
            entry["home_team_id"] = game.xpath('.//*[@data-stat="home_team_name"]//@csk').get()[:3]
            entry["home_pts"] = game.xpath('.//*[@data-stat="home_pts"]//text()').get()
            entry["overtimes"] = game.xpath('.//*[@data-stat="overtimes"]//text()').get()
            entry["attendance"] = game.xpath('.//*[@data-stat="attendance"]//text()').get()
            entry["game_remarks"] = game.xpath('.//*[@data-stat="game_remarks"]//text()').get()

            entries.append(entry)

        if entries:
            yield { 'file_name': season, 
                    'type': 'schedule', 
                    'dir': 'schedule/playoffs', 
                    'data': entries, 
                    'fieldnames': self.get_game_keys() }

    def get_game_keys(self):
        keys = [
            "game_id",
            "date",
            "start_time",
            "visitor_team",
            "visitor_team_id",
            "visitor_pts",
            "home_team",
            "home_team_id",
            "home_pts",
            "overtimes",
            "attendance",
            "game_remarks"
        ]
        return keys

    def get_game_entry(self):
        entry = {}
        keys = self.get_game_keys()

        for key in keys:
            entry[key] = None

        return entry
