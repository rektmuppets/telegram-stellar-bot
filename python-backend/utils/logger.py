import logging

def setup_logger():
    """
    Configures logging for the bot.
    """
    logging.basicConfig(
        level=logging.INFO,  # Change to DEBUG for more detailed logs
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("bot.log"),  # Logs to bot.log
            logging.StreamHandler()  # Logs to the console
        ]
    )
