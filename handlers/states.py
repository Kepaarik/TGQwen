from aiogram.fsm.state import State, StatesGroup

class TransactionState(StatesGroup):
    wait_currency = State()
    wait_amount = State()

class EventState(StatesGroup):
    wait_date = State()
    wait_desc = State()

class EditEventState(StatesGroup):
    wait_new_date = State()
    wait_new_desc = State()
    wait_new_recurrence = State()
