import random
import asyncio

class Stock:
    def __init__(self, name, price):
        self.name = name
        self.price = price
        self.previous_price = price
        self.is_listed = True

    async def update_price(self):
        if not self.is_listed:
            return
        self.previous_price = self.price
        self.price *= random.uniform(0.9, 1.1)
        self.price = round(self.price)

        if self.price < 5:
            await self.delist()

    async def delist(self):
        self.is_listed = False
        await self.schedule_relist()

    async def schedule_relist(self):
        await asyncio.sleep(3600)
        await self.relist()

    async def relist(self):
        self.is_listed = True
        self.price = max(10, round(self.previous_price * random.uniform(0.9, 1.1)))

    def price_change(self):
        return self.price - self.previous_price