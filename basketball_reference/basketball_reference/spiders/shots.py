# -*- coding: utf-8 -*-
import scrapy
from scrapy.linkextractors import LinkExtractor
from datetime import date

import re, math

class ShotsSpider(scrapy.Spider):
    name = 'shots'
    allowed_domains = ['basketball-reference.com']
    start_urls = []

    def __init__(self, **kwargs):
        '''
        Expects seasons and months.
        '''
        if 'seasons' in kwargs:
            self.seasons = [int(x) for x in kwargs['seasons'].split(',')]
        else:
            self.seasons = []

        if 'from_season' and 'to_season' in kwargs:
            from_season = int(kwargs['from_season'])
            to_season = int(kwargs['to_season'])

            self.seasons = [x for x in range(from_season, to_season + 1)]

        if 'months' in kwargs:
            if kwargs['months'] == 'all':
                self.months = [x for x in range(12)]
            else:
                self.months = [int(x) - 1 for x in kwargs['months'].split(',')]
        else:
            if self.seasons:
                self.months = self.months = [x for x in range(12)]
            else:
                self.months = ()

        if 'date' in kwargs:
            if kwargs['date'] == 'today':
                self.seasons = [date.today().year - 1, date.today().year, date.today().year + 1]
                self.months = [date.today().month - 1]
            if kwargs['date'] == 'season':
                self.seasons = [date.today().year - 1, date.today().year, date.today().year + 1]
                self.months = [x for x in range(12)]

        if 'games' in kwargs:
            if self.seasons:
                self.games = ()
            else:
                self.games = [x for x in kwargs['games'].split(',')]
        else:
            self.games = ()


    def start_requests(self):
        '''
        Initial requests that will be processed, based on the arguments passed.
        '''
        BASE_URL = 'https://www.basketball-reference.com'
        SCHEDULE_URL = '/leagues/NBA_{season}_games-{month}.html'
        MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 
                        'august', 'september', 'october', 'november', 'december']

        for season in self.seasons:
            for month in self.months:
                url = BASE_URL + SCHEDULE_URL.format(
                            season=season, month=MONTHS[month])
                yield scrapy.Request(url, callback=self.parse_schedule)
        
        for game_id in self.games:
            url = '{}/boxscores/shot-chart/{}.html'.format(BASE_URL, game_id)
            yield scrapy.Request(url, callback=self.parse_game)


    def parse_schedule(self, response):
        '''
        Extracts information about the schedule.
        '''
        if not self.only_schedules:
            for a in response.xpath('//a/@href'):
                url = a.extract()
                if re.match(r'/boxscores/shot-chart/(\d){9}([A-Z]){3}\.html', url):
                    yield response.follow(url, callback=self.parse_game)

            
    def parse_game(self, response):
        game_id = re.search(r"/([\dA-Z]*)?.html", response.url).group(1)

        shot_entries = []
        
        teams = response.xpath('//div[starts-with(@id, "shots-")]')

        for team_shots in teams:
            team_id = re.search(r"shots-([A-Z]{3})", team_shots.attrib['id']).group(1)
            
            shots = team_shots.xpath('*[@tip]')
            
            for shot in shots:
                html_tip = shot.attrib['tip']
                quarter = re.search(r'([\w\s]+),', html_tip).group(1)
                time = re.search(r' ([\d]{1,2}:[\d]{2}.[\d]{1,2}) ', html_tip).group(1)

                if bool(re.search(r'2-pointer', html_tip)):
                    points = 2
                elif bool(re.search(r'3-pointer', html_tip)):
                    points = 3


                html_class = shot.attrib['class']
                make = bool(re.search(r' make$', html_class))
                player_id = re.search(r' p-([a-z]{1,7}[\d]{2}) ', html_class).group(1)

                html_style = shot.attrib['style']
                x = re.search(r'left:([\d]*)px', html_style).group(1)
                y = re.search(r'top:([\d]*)px', html_style).group(1)
                
                distance = self.get_distance_cm(x, y)


                entry = self.get_shot_entry()
                entry['game_id'] = game_id
                entry['team_id'] = team_id
                entry['player_id'] = player_id
                entry['quarter'] = quarter
                entry['make'] = make
                entry['points'] = points
                entry['x_px'] = x
                entry['y_px'] = y
                entry['distance_cm'] = round(distance)

                shot_entries.append(entry)
                    
            yield { 'file_name': game_id[4:], 
                    'type': 'shot', 
                    'dir': 'games/shots/{}'.format(game_id[:4]), 
                    'data': shot_entries,
                    'fieldnames': self.get_shot_keys() }
        


    
    def get_shot_keys(self):
        keys = [
            'game_id',
            'team_id',
            'player_id',
            'quarter',
            'make',
            'points',
            'x_px',
            'y_px',
            'distance_cm',
        ]
        return keys


    def get_shot_entry(self):
        entry = {}
        keys = self.get_shot_keys()
        for key in keys:
            entry[key] = None
        return entry



    def get_distance_cm(self, x, y):
        FT_TO_CM = 30.48
        COURT_SIZE_PX = {'x': 500, 'y': 472}
        COURT_SIZE_FT = {'x': 50, 'y': 94 / 2}
        COURT_SIZE_CM = {'x': COURT_SIZE_FT['x'] * FT_TO_CM, 'y': COURT_SIZE_FT['y'] * FT_TO_CM}
        POS_CM = {'x': float(x) / 10 * FT_TO_CM, 'y': float(y) / 10 * FT_TO_CM}
        HOOP_POSITION_CM = {'x': COURT_SIZE_CM['x'] / 2, 'y': 160.02}
        squared_x = (POS_CM['x'] - HOOP_POSITION_CM['x']) ** 2
        squared_y = (POS_CM['y'] - HOOP_POSITION_CM['y']) ** 2
        return math.sqrt(squared_x + squared_y)

