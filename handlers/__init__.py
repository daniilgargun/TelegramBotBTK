from aiogram import Router
from .start import router as start_router
from .user import router as user_router  
from .admin import router as admin_router
from .holiday_greetings import router as holiday_router


main_router = Router()
main_router.include_router(start_router)
main_router.include_router(user_router)  
main_router.include_router(admin_router)
main_router.include_router(holiday_router)

