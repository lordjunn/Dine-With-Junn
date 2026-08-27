from typing import List, Optional
from dataclasses import dataclass, field

@dataclass
class EtcExpenseItem:
    label: str
    amount: float
    day: Optional[int] = None

@dataclass
class Expenses:
    rental: float = 0.0
    utilities: float = 0.0
    petrol: float = 0.0
    etc: List[EtcExpenseItem] = field(default_factory=list)

@dataclass
class ArchiveMetadata:
    era: str = "Unknown grounds"
    teaser: str = ""
    image: str = ""

@dataclass
class OutroMetadata:
    title: str = ""
    image: str = ""
    prose: str = ""

@dataclass
class MealItem:
    dish_name: str
    restaurant: str
    price_str: str = ""
    price: float = 0.0
    meal_type: str = "Lunch"  # Lunch, Dinner, Breakfast, etc.
    image: str = ""
    description: str = ""
    items: List[str] = field(default_factory=list)  # itemized ingredients/details

@dataclass
class DayEntry:
    date_str: str  # YYYY-MM-DD
    day_of_week: str  # e.g. Wednesday
    meals: List[MealItem] = field(default_factory=list)

@dataclass
class MonthData:
    year: int
    month: int
    slug: str  # e.g. 2026-07
    title: str = ""
    nom_nom_days: Optional[int] = None
    reasons: List[str] = field(default_factory=list)
    intro_text: str = ""
    archive: ArchiveMetadata = field(default_factory=ArchiveMetadata)
    outro: OutroMetadata = field(default_factory=OutroMetadata)
    expenses: Expenses = field(default_factory=Expenses)
    days: List[DayEntry] = field(default_factory=list)

@dataclass
class MonthAnalytics:
    purely_food_expenses: float = 0.0
    breakfast_total: float = 0.0
    breakfast_count: int = 0
    breakfast_average: float = 0.0
    lunch_total: float = 0.0
    lunch_count: int = 0
    lunch_average: float = 0.0
    dinner_total: float = 0.0
    dinner_count: int = 0
    dinner_average: float = 0.0
    average_cost_per_day: float = 0.0
    etc_expenses_total: float = 0.0
    total_cash_damage: float = 0.0
    
    # Chart.js visualization datasets
    chart_labels: List[str] = field(default_factory=list)
    chart_daily_costs: List[float] = field(default_factory=list)
    chart_breakfast_costs: List[float] = field(default_factory=list)
    chart_lunch_costs: List[float] = field(default_factory=list)
    chart_dinner_costs: List[float] = field(default_factory=list)
