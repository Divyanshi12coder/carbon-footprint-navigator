"""Seed command: `python -m app.seed [--factors] [--demo]`.

Without flags it follows SEED_EMISSION_FACTORS / SEED_DEMO_DATA from the environment.
Safe to run repeatedly (idempotent).
"""

import argparse
import logging

from app.carbon.factors import seed_emission_factors
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.seed import seed_demo_user

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("seed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--factors", action="store_true", help="Seed emission factors")
    parser.add_argument("--demo", action="store_true", help="Seed the demo user with ~6 months of activities")
    args = parser.parse_args()
    settings = get_settings()
    do_factors = args.factors or (not args.demo and settings.seed_emission_factors) or args.demo
    do_demo = args.demo or (not args.factors and settings.seed_demo_data)

    with SessionLocal() as db:
        if do_factors:
            created = seed_emission_factors(db)
            logger.info("Emission factors: %d new", created)
        if do_demo:
            user = seed_demo_user(db, settings.demo_user_email, settings.demo_user_password)
            if user:
                logger.info("Demo login: %s / (DEMO_USER_PASSWORD)", settings.demo_user_email)


if __name__ == "__main__":
    main()
