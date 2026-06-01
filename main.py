import asyncio
from train_watcher import TrainWatcherEngine

async def run_bot():
    bot = TrainWatcherEngine(config_source="gui_config.json")
    await bot.start()

if __name__ == "__main__":
    asyncio.run(run_bot())
