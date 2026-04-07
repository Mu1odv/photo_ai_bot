from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    """User states for photo/video processing"""
    waiting_for_photo = State()  # Waiting for user to upload a photo
    waiting_for_print_option = State()  # Waiting for print option selection (frame/digital)
