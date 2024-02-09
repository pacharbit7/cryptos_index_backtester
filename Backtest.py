# -*- coding: utf-8 -*-
"""
Created on Sun Dec 31 18:26:38 2023

@author: paul-
"""
#classe centrale du backtesting, ele viient itéréer ligne par ligne sur l'attribut df de l'objet dataloader entre les dats de début et de fin de la strategie
# l'interêt est de récuperer la "current_date" qui la date actuelle au moment du backtesting 
class Backtest:

    def __init__(self, strategy, data_loader, start_date, end_date):
        self.strategy = strategy
        self.data_loader = data_loader
        self.start_date = start_date
        self.end_date = end_date
        self.current_date = None

    def run(self):
        for current_date, daily_data in self.generate_data():
            self.current_date = current_date
            self.strategy.apply_strategy()

    def generate_data(self):
        for date, data in self.data_loader.df.loc[self.start_date:self.end_date].iterrows():
            yield date, data