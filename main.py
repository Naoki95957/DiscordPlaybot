from bot import PlayBot
from bot_terminal import BotTerminal    

def main():
    bot = PlayBot()
    bot.enable_print_statements(False)
    terminal = BotTerminal(bot).start()
    
if __name__ == "__main__":
    main()