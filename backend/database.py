from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.config import settings


engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from backend import models  # noqa: F401 – Modelle registrieren
    Base.metadata.create_all(bind=engine)
    _seed_config()
    _seed_universe()


def _seed_universe():
    from backend.universe.loader import load_static_universe
    with SessionLocal() as db:
        load_static_universe(db)


def _seed_config():
    with SessionLocal() as db:
        defaults = [
            ("weight_fundamental", "40", "Gewichtung Fundamentalanalyse (%)"),
            ("weight_technical",   "35", "Gewichtung Technische Analyse (%)"),
            ("weight_sentiment",   "25", "Gewichtung Sentiment-Analyse (%)"),
            ("zone1_min_score",    "76", "Mindestscore Zone 1"),
            ("zone2_min_score",    "61", "Mindestscore Zone 2"),
            ("zone3_min_score",    "41", "Mindestscore Zone 3"),
            ("alert_delta_1d",     "15", "Δ1T-Schwelle für Sofort-Alert"),
            ("exit_score_drop",    "15", "Score-Rückgang für Exit-Warnung"),
            ("exit_ko_distance",   "8",  "KO-Abstand % für Exit-Warnung"),
            ("exit_expiry_weeks",  "3",  "Restlaufzeit-Warnung in Wochen"),
            ("exit_bull_ratio",    "35", "Bullish-Ratio % für Sentiment-Warnung"),
            ("scan_rotation_idx",  "0",  "Rotation-Index für Zone-4-Scan"),
            ("zone4_daily_count",  "200","Anzahl Zone-4-Aktien pro Scan"),
        ]
        for key, value, desc in defaults:
            db.execute(
                text(
                    "INSERT OR IGNORE INTO configuration(key, value, description, updated_at) "
                    "VALUES(:k,:v,:d,datetime('now'))"
                ),
                {"k": key, "v": value, "d": desc},
            )
        db.commit()
