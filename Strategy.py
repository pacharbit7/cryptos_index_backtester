# -*- coding: utf-8 -*-
"""
Created on Sun Dec 31 18:27:13 2023

@author: paul-
"""
#classe asbtraite utilisée pour specifier lés méthodes obligatorie de nos strategies
#nos 3 stratégies sont construitent sur une logique très similaire
class AbstractStrategy(ABC):

    @abstractmethod
    def calculate_weights(self):
        pass

    @abstractmethod
    def apply_strategy(self):
        pass


class MarketCapStrategy(AbstractStrategy):
    
    def __init__(self, data, market_caps, rebalancing_window, initial_capital, start_date, end_date):
        self.data = data
        self.market_caps = market_caps
        self.weights = [{coin: [0] for coin in data.symbols_list}] # initialisation des poids à 0
        self.rebalancing_window = rebalancing_window
        self.initial_capital = initial_capital
        
        self.start_date = start_date
        dates = pd.date_range(start=start_date, end=end_date)
        self.portfolio = pd.DataFrame(0,index=dates, columns=data.symbols_list)
        self.portfolio_value = pd.DataFrame(0,index=dates, columns=['Value'])
        
        start_date_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        available_assets = [coin for coin in data.symbols_list if start_date_datetime in data.dataframes[coin].index]
        #available_assets est utilisé pour ne répartir le capital qu'entre les actifs qui existente à la currente_date, c'est pourquoi un attribut self.available_assets sera ensuite instancié
        # et régulièrement mis à jour
        
        num_assets = len(available_assets)
        initial_allocation = initial_capital / num_assets
        
        for coin in data.symbols_list:
            allocation = initial_allocation if coin in available_assets else 0
            self.portfolio.at[start_date, coin] = allocation
        #pour les coins existants à la date de départ, on va venir répartir le capital initial équitablement            
            
        self.portfolio_value.at[start_date, 'Value'] = initial_capital
               
        self.last_rebalancing = None
        
        self.backtest = Backtest(self, data, start_date, end_date)
        self.backtest.run() 

    #renvoie un dictionnaire de poids
    def calculate_weights(self):
    
        self.available_assets = [coin for coin in self.data.symbols_list if self.backtest.current_date in self.data.dataframes[coin].index]
        current_market_caps = self.market_caps.loc[self.backtest.current_date]

        total_market_cap = current_market_caps[[coin for coin in self.available_assets if coin in current_market_caps.index]].sum()
    
        weights = {}
        for coin in self.data.symbols_list:
            if (coin in self.available_assets) and (coin in current_market_caps.index):
                #on vient vérifier qu'on dispose des prix et des markets_caps
                weights[coin] = current_market_caps[coin] / total_market_cap
            else:
                weights[coin] = 0
        return weights
    
    #renvoie le rendement d'un jour sur l'autre
    def calculate_returns(self,coin):
        current_date_index = self.data.dataframes[coin].index.get_loc(self.backtest.current_date)
        self.previous_date = self.data.dataframes[coin].index[current_date_index - 1]
        previous_value = float(self.data.dataframes[coin].loc[self.previous_date, 'Close'])
        current_value = float(self.data.dataframes[coin].loc[self.backtest.current_date, 'Close'])
        r = np.log(current_value / previous_value)
        return r
    
    def maj_portfolio_value(self):
        
        for coin in self.available_assets:
            r = self.calculate_returns(coin)
            current_value = self.portfolio.loc[self.previous_date, coin] * (1+r)
            self.portfolio.at[self.backtest.current_date, coin] = current_value
            
        total_portfolio_value = self.portfolio.loc[self.backtest.current_date].sum()
        self.portfolio_value.at[self.backtest.current_date, 'Value'] = total_portfolio_value
            

    def rebalancing(self):
        
        weights = self.calculate_weights()
        if self.backtest.current_date != datetime.strptime(self.start_date, '%Y-%m-%d'):
            #cette méthode ne devient fonctionnel qu'à partir de la deuxième date
            
            self.weights.append(weights)
            self.maj_portfolio_value()

            for coin in self.available_assets:
                
                if self.portfolio.loc[self.previous_date, coin] != 0:
                    r = self.calculate_returns(coin)
                    current_value = self.portfolio.loc[self.previous_date, coin] * (1+r) 
                    
                    self.portfolio.at[self.backtest.current_date, coin] = current_value
                    target = self.portfolio_value.loc[self.backtest.current_date, 'Value']*self.weights[-1][coin]
                    
                    if target > current_value:
                        self.go_long(coin)
                        
                    elif target < current_value:
                        self.go_short(coin)
                else:
                    self.portfolio.at[self.backtest.current_date, coin] = self.portfolio_value.loc[self.backtest.current_date, 'Value']*self.weights[-1][coin]
    
    #vient modifier la position d'un actif précis au sein du portefeuille
    def go_short(self, coin):
        
        r = self.calculate_returns(coin)
        new_value = self.portfolio.at[self.previous_date, coin] * (1 + r)
        target_value = self.weights[-1][coin] * self.portfolio_value.loc[self.backtest.current_date, 'Value']
        
        amount_to_sell = new_value - target_value      
        self.portfolio.at[self.backtest.current_date, coin] -= amount_to_sell
        
    def go_long(self, coin):
        
        r = self.calculate_returns(coin)
        new_value = self.portfolio.at[self.previous_date, coin] * (1 + r)
        target_value = self.weights[-1][coin] * self.portfolio_value.loc[self.backtest.current_date, 'Value']
    
        amount_to_buy = target_value - new_value  
        self.portfolio.at[self.backtest.current_date, coin] += amount_to_buy
        
    # cette méthode va venir rebalancer le portefeuille si le rebalancement au date de rebalancement, et calculer les valeurs de protefeuilles sinon
    def apply_strategy(self):
        if self.last_rebalancing is None or (self.backtest.current_date - self.last_rebalancing).days >= self.rebalancing_window:
            self.rebalancing()
            self.last_rebalancing = self.backtest.current_date
        else:
            self.available_assets = [coin for coin in self.data.symbols_list if self.backtest.current_date in self.data.dataframes[coin].index]
            for coin in self.available_assets:
                current_date_index = self.data.dataframes[coin].index.get_loc(self.backtest.current_date)
                previous_date = self.data.dataframes[coin].index[current_date_index - 1]
                previous_value = float(self.data.dataframes[coin].loc[previous_date, 'Close'])
                current_value = float(self.data.dataframes[coin].loc[self.backtest.current_date, 'Close'])
                
                r = np.log(current_value) - np.log(previous_value)
                new_value = self.portfolio.loc[previous_date, coin] * (1 + r)
                self.portfolio.at[self.backtest.current_date, coin] = new_value
                
            
            self.portfolio_value.at[self.backtest.current_date, 'Value'] = self.portfolio.loc[self.backtest.current_date].sum()
              
class EqualWeightStrategy(AbstractStrategy):
    
    def __init__(self, data, rebalancing_window, initial_capital, start_date, end_date):
        self.data = data
        self.weights = [{coin: [0] for coin in data.symbols_list}] # initialisation des poids à 0
        self.rebalancing_window = rebalancing_window
        self.initial_capital = initial_capital
        
        #end_date = datetime.strptime(end_date, '%Y-%m-%d')     
        #end_date -= timedelta(days=1)
        #end_date = end_date.strftime('%Y-%m-%d')
        
        dates = pd.date_range(start=start_date, end=end_date)
        self.portfolio = pd.DataFrame(0,index=dates, columns=data.symbols_list)
        self.portfolio_value = pd.DataFrame(0,index=dates, columns=['Value'])
        
        start_date_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        available_assets = [coin for coin in data.symbols_list if start_date_datetime in data.dataframes[coin].index]
        #ne repartir le acpital inital qu'entre les cryptos existentes au depart
        
        num_assets = len(available_assets)
        initial_allocation = initial_capital / num_assets
        
        for coin in data.symbols_list:
            allocation = initial_allocation if coin in available_assets else 0
            self.portfolio.at[start_date, coin] = allocation
            
            
        self.portfolio_value.at[start_date, 'Value'] = initial_capital
       
        
        self.last_rebalancing = None
        
        self.backtest = Backtest(self, data, start_date, end_date)
        self.backtest.run()

    def calculate_weights(self):
        
        self.available_assets = [coin for coin in self.data.symbols_list if self.backtest.current_date in self.data.dataframes[coin].index]
        num_assets = len(self.available_assets)
        weight = 1 / num_assets
        weights = {coin: weight for coin in self.available_assets}
    
        for coin in self.data.symbols_list:
            if coin not in self.available_assets:
                weights[coin] = 0
                
        return weights
    
    def calculate_returns(self,coin):
        current_date_index = self.data.dataframes[coin].index.get_loc(self.backtest.current_date)
        self.previous_date = self.data.dataframes[coin].index[current_date_index - 1]
        previous_value = float(self.data.dataframes[coin].loc[self.previous_date, 'Close'])
        current_value = float(self.data.dataframes[coin].loc[self.backtest.current_date, 'Close'])
        r = np.log(current_value / previous_value)
        return r
    
    def maj_portfolio_value(self):
        
        for coin in self.available_assets:
            r = self.calculate_returns(coin)
            current_value = self.portfolio.loc[self.previous_date, coin] * (1+r)
            self.portfolio.at[self.backtest.current_date, coin] = current_value
            
        total_portfolio_value = self.portfolio.loc[self.backtest.current_date].sum()
        self.portfolio_value.at[self.backtest.current_date, 'Value'] = total_portfolio_value
            
            
            
  
    def rebalancing(self):
        weights = self.calculate_weights()
        if self.backtest.current_date != datetime.strptime(start_date, '%Y-%m-%d'):
            
            self.weights.append(weights)
            self.maj_portfolio_value()

            for coin in self.available_assets:
                
                if self.portfolio.loc[self.previous_date, coin] != 0:
                    r = self.calculate_returns(coin)
                    current_value = self.portfolio.loc[self.previous_date, coin] * (1+r) #problème ici, si première valeur = 0 ça se mettra pas à jour
                    
                    self.portfolio.at[self.backtest.current_date, coin] = current_value
                    target = self.portfolio_value.loc[self.backtest.current_date, 'Value']/len(self.available_assets)
                    
                    if target > current_value:
                        self.go_long(coin)
                        
                    elif target < current_value:
                        self.go_short(coin)
                else:
                    self.portfolio.at[self.backtest.current_date, coin] = self.portfolio_value.at[self.backtest.current_date, 'Value']/len(self.available_assets)
                    
            
            
    def go_short(self, coin):
        
        r = self.calculate_returns(coin)
        new_value = self.portfolio.at[self.previous_date, coin] * (1 + r)
        target_value = self.weights[-1][coin] * self.portfolio_value.loc[self.backtest.current_date, 'Value']
        
        amount_to_sell = new_value - target_value      
        self.portfolio.at[self.backtest.current_date, coin] -= amount_to_sell
        
    def go_long(self, coin):
        
        r = self.calculate_returns(coin)
        new_value = self.portfolio.at[self.previous_date, coin] * (1 + r)
        target_value = self.weights[-1][coin] * self.portfolio_value.loc[self.backtest.current_date, 'Value']
    
        amount_to_buy = target_value - new_value  
        self.portfolio.at[self.backtest.current_date, coin] += amount_to_buy
        
    def apply_strategy(self):
        if self.last_rebalancing is None or (self.backtest.current_date - self.last_rebalancing).days >= self.rebalancing_window:
            self.rebalancing()
            self.last_rebalancing = self.backtest.current_date
        else:
            self.available_assets = [coin for coin in self.data.symbols_list if self.backtest.current_date in self.data.dataframes[coin].index]
            for coin in self.available_assets:
                current_date_index = self.data.dataframes[coin].index.get_loc(self.backtest.current_date)
                previous_date = self.data.dataframes[coin].index[current_date_index - 1]
                previous_value = float(self.data.dataframes[coin].loc[previous_date, 'Close'])
                current_value = float(self.data.dataframes[coin].loc[self.backtest.current_date, 'Close'])
                
                r = np.log(current_value) - np.log(previous_value)
                new_value = self.portfolio.loc[previous_date, coin] * (1 + r)
                self.portfolio.at[self.backtest.current_date, coin] = new_value
                
            
            self.portfolio_value.at[self.backtest.current_date, 'Value'] = self.portfolio.loc[self.backtest.current_date].sum()
            
class PriceWeightedStrategy(AbstractStrategy):
    
    def __init__(self, data, rebalancing_window, initial_capital, start_date, end_date):
        self.data = data
        self.weights = [{coin: [0] for coin in data.symbols_list}] # initialisation des poids à 0
        self.rebalancing_window = rebalancing_window
        self.initial_capital = initial_capital
        
        dates = pd.date_range(start=start_date, end=end_date)
        self.portfolio = pd.DataFrame(0,index=dates, columns=data.symbols_list)
        self.portfolio_value = pd.DataFrame(0,index=dates, columns=['Value'])
        
        start_date_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        available_assets = [coin for coin in data.symbols_list if start_date_datetime in data.dataframes[coin].index]
        #ne repartir le acpital inital qu'entre les cryptos existentes au depart
        
        prices = {coin: float(self.data.dataframes[coin].loc[start_date_datetime]['Close']) for coin in available_assets}
        total_price = sum(prices.values())
        
        initial_allocation = {coin: self.initial_capital * price / total_price for coin, price in prices.items()}
        
        for coin in data.symbols_list:
            allocation = allocation = initial_allocation[coin] if coin in available_assets else 0
            self.portfolio.at[start_date, coin] = allocation
            
      
        self.portfolio_value.at[start_date, 'Value'] = initial_capital
       
        
        self.last_rebalancing = None
        
        self.backtest = Backtest(self, data, start_date, end_date)
        self.backtest.run()

    def calculate_weights(self):
       # les poids sont calculées par rapport au closing price
       self.available_assets = [coin for coin in self.data.symbols_list if self.backtest.current_date in self.data.dataframes[coin].index]
       weights = {coin: float(self.data.dataframes[coin].loc[self.backtest.current_date]['Close']) for coin in self.available_assets}
       
       # normalisation des poids à 1
       total_price = sum(weights.values())
       weights = {coin: price / total_price for coin, price in weights.items()}
       
       return weights
    
    def calculate_returns(self,coin):
        current_date_index = self.data.dataframes[coin].index.get_loc(self.backtest.current_date)
        self.previous_date = self.data.dataframes[coin].index[current_date_index - 1]
        previous_value = float(self.data.dataframes[coin].loc[self.previous_date, 'Close'])
        current_value = float(self.data.dataframes[coin].loc[self.backtest.current_date, 'Close'])
        r = np.log(current_value / previous_value)
        return r
    
    def maj_portfolio_value(self):
        
        for coin in self.available_assets:
            r = self.calculate_returns(coin)
            current_value = self.portfolio.loc[self.previous_date, coin] * (1+r)
            self.portfolio.at[self.backtest.current_date, coin] = current_value
            
        total_portfolio_value = self.portfolio.loc[self.backtest.current_date].sum()
        self.portfolio_value.at[self.backtest.current_date, 'Value'] = total_portfolio_value
            
            
            
    
    def rebalancing(self):
        weights = self.calculate_weights()
        if self.backtest.current_date != datetime.strptime(start_date, '%Y-%m-%d'):
            
            self.weights.append(weights)
            self.maj_portfolio_value()

            for coin in self.available_assets:
                
                if self.portfolio.loc[self.previous_date, coin] != 0:
                    r = self.calculate_returns(coin)
                    current_value = self.portfolio.loc[self.previous_date, coin] * (1+r)
                    
                    self.portfolio.at[self.backtest.current_date, coin] = current_value
                    target = self.portfolio_value.loc[self.backtest.current_date, 'Value'] * self.weights[-1][coin]
                    
                    if target > current_value:
                        self.go_long(coin)
                        
                    elif target < current_value:
                        self.go_short(coin)
                else:
                    self.portfolio.at[self.backtest.current_date, coin] = self.portfolio_value.loc[self.backtest.current_date, 'Value']*self.weights[-1][coin]
                    
            
            
    def go_short(self, coin):
        
        r = self.calculate_returns(coin)
        new_value = self.portfolio.at[self.previous_date, coin] * (1 + r)
        target_value = self.weights[-1][coin] * self.portfolio_value.loc[self.backtest.current_date, 'Value']
        
        amount_to_sell = new_value - target_value      
        self.portfolio.at[self.backtest.current_date, coin] -= amount_to_sell
        
    def go_long(self, coin):
        
        r = self.calculate_returns(coin)
        new_value = self.portfolio.at[self.previous_date, coin] * (1 + r)
        target_value = self.weights[-1][coin] * self.portfolio_value.loc[self.backtest.current_date, 'Value']
    
        amount_to_buy = target_value - new_value  
        self.portfolio.at[self.backtest.current_date, coin] += amount_to_buy
        
    def apply_strategy(self):
        if self.last_rebalancing is None or (self.backtest.current_date - self.last_rebalancing).days >= self.rebalancing_window:
            self.rebalancing()
            self.last_rebalancing = self.backtest.current_date
        else:
            self.available_assets = [coin for coin in self.data.symbols_list if self.backtest.current_date in self.data.dataframes[coin].index]
            for coin in self.available_assets:
                current_date_index = self.data.dataframes[coin].index.get_loc(self.backtest.current_date)
                previous_date = self.data.dataframes[coin].index[current_date_index - 1]
                previous_value = float(self.data.dataframes[coin].loc[previous_date, 'Close'])
                current_value = float(self.data.dataframes[coin].loc[self.backtest.current_date, 'Close'])
                
                r = np.log(current_value) - np.log(previous_value)
                new_value = self.portfolio.loc[previous_date, coin] * (1 + r)
                self.portfolio.at[self.backtest.current_date, coin] = new_value
                
            self.portfolio_value.at[self.backtest.current_date, 'Value'] = self.portfolio.loc[self.backtest.current_date].sum()