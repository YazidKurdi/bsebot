"""
A file for enums
"""

from enum import IntEnum


class TransactionTypes(IntEnum):
    """
    TransactionTypes are the type of "transactions" that can take place when a user gains/loses eddies.
    """
    HISTORY_START = 1
    BET_PLACE = 2
    BET_WIN = 3
    GIFT_GIVE = 4
    GIFT_RECEIVE = 5
    DAILY_SALARY = 6
    USER_CREATE = 7
    BET_REFUND = 8
    LOAN_TAKE = 9
    LOAN_REPAYMENT = 10
    LOAN_COLLECTION = 11
    ADMIN_GIVE = 12
    ADMIN_TAKE = 13
    POINT_ROT_LOSS = 14
    POINT_ROT_GAIN = 15
    REV_TICKET_BUY = 16
    REV_TICKET_WIN = 17
    REV_TICKET_KING_WIN = 18
    REV_TICKET_KING_LOSS = 19
    REV_SUPPORT = 20
    REV_OVERTHROW = 21
    SUPPORTER_LOST_REVOLUTION = 22
    TAX_GAINS = 23
    BET_TAX = 24
    MONTHLY_AWARDS_PRIZE = 25
    ANNUAL_AWARDS_PRIZE = 26
    OVERRIDE = 99


class ActivityTypes(IntEnum):
    """
    ActivityTypes are types of activity that we are tracking (that aren't transactions)
    """
    KING_GAIN = 1
    KING_LOSS = 2
    LOAN_TAKE = 3
    LOAN_REPAYMENT = 4
    LOAN_COLLECTION = 5
    BSEDDIES_VIEW = 6
    BSEDDIES_LEADERBOARD = 7
    BSEDDIES_HIGHSCORES = 8
    BSEDDIES_ACTIVE = 9
    BSEDDIES_PENDING = 10
    BSEDDIES_GIFT = 11
    BSEDDIES_BET_CLOSE = 12
    BSEDDIES_BET_CREATE = 13
    BSEDDIES_BET_PLACE = 14
    BSEDDIES_TRANSACTIONS = 15
    BSEDDIES_NOTIFICATION_TOGGLE = 16
    BSEDDIES_LOAN_TAKE = 17
    BSEDDIES_LOAN_REPAY = 18
    BSEDDIES_LOAN_VIEW = 19
    BSEDDIES_AUTOGENERATE = 20
    BSEDDIES_ADMIN_GIVE = 21
    BSEDDIES_ADMIN_TAKE = 22
    BSEDDIES_ADMIN_CHANGE = 23
    BSEDDIES_KING = 24
    SERVER_LEAVE = 25
    SERVER_JOIN = 26
    BSE_SERVER_ON = 27
    BSE_SERVER_OFF = 28
    BSE_GAME_SERVER_TOGGLE = 29
    BSEDDIES_PREDICT = 30
    BSEDDIES_SET_TAX_RATE = 31
    BSEDDIES_ACTUAL_SET_TAX_RATE = 32
    BSEDDIES_BET_CANCEL = 33


class AwardsTypes(IntEnum):
    """_summary_

    Args:
        IntEnum (_type_): _description_
    """
    MOST_MESSAGES = 1
    LEAST_MESSAGES = 2
    LONGEST_MESSAGE = 3
    BEST_AVG_WORDLE = 4
    MOST_BETS = 5
    MOST_EDDIES_BET = 6
    MOST_EDDIES_LOST = 7
    MOST_EDDIES_WON = 8
    LONGEST_KING = 9
    TWITTER_ADDICT = 10
    MASTURBATOR = 11
    BIG_MEMER = 12
    REACT_KING = 13


class StatTypes(IntEnum):
    NUMBER_OF_MESSAGES = 1
    AVERAGE_MESSAGE_LENGTH_CHARS = 2
    AVERAGE_MESSAGE_LENGTH_WORDS = 3
    BUSIEST_CHANNEL = 4
    BUSIEST_DAY = 5
    NUMBER_OF_BETS = 6
    SALARY_GAINS = 7
    AVERAGE_WORDLE_VICTORY = 8
    EDDIES_PLACED = 9
    EDDIES_WIN = 10
    MOST_POPULAR_CHANNEL = 11
