from datetime import datetime
from typing import List, Tuple
from pipeline.schema import MonthData, MonthAnalytics, DayEntry, MealItem

class SpendingAnalyticsEngine:
    """Calculates financial statistics, averages, and chart datasets for a MonthData instance."""

    def compute(self, month_data: MonthData) -> MonthAnalytics:
        """Computes complete analytics for a month."""
        purely_food = 0.0
        breakfast_total = 0.0
        breakfast_count = 0
        lunch_total = 0.0
        lunch_count = 0
        dinner_total = 0.0
        dinner_count = 0

        chart_labels: List[str] = []
        chart_daily_costs: List[float] = []
        chart_breakfast_costs: List[float] = []
        chart_lunch_costs: List[float] = []
        chart_dinner_costs: List[float] = []

        for day in month_data.days:
            # Format date label e.g., '01 (Wed)'
            label = self._format_day_label(day.date_str, day.day_of_week)
            chart_labels.append(label)

            day_food_cost = 0.0
            day_breakfast = 0.0
            day_lunch = 0.0
            day_dinner = 0.0

            for meal in day.meals:
                price = meal.price
                day_food_cost += price
                m_type = meal.meal_type.lower()

                if "breakfast" in m_type:
                    day_breakfast += price
                    if price > 0 or meal.price_str.lower() == "free":
                        breakfast_count += 1
                elif "lunch" in m_type:
                    day_lunch += price
                    if price > 0 or meal.price_str.lower() == "free":
                        lunch_count += 1
                elif "dinner" in m_type:
                    day_dinner += price
                    if price > 0 or meal.price_str.lower() == "free":
                        dinner_count += 1

            purely_food += day_food_cost
            breakfast_total += day_breakfast
            lunch_total += day_lunch
            dinner_total += day_dinner

            chart_daily_costs.append(round(day_food_cost, 2))
            chart_breakfast_costs.append(round(day_breakfast, 2))
            chart_lunch_costs.append(round(day_lunch, 2))
            chart_dinner_costs.append(round(day_dinner, 2))

        # Averages
        avg_breakfast = (breakfast_total / breakfast_count) if breakfast_count > 0 else 0.0
        avg_lunch = (lunch_total / lunch_count) if lunch_count > 0 else 0.0
        avg_dinner = (dinner_total / dinner_count) if dinner_count > 0 else 0.0

        # Average per day: divide by nom_nom_days if set > 0, otherwise active days with meals
        days_with_meals = len([d for d in month_data.days if len(d.meals) > 0])
        active_days_count = month_data.nom_nom_days if (month_data.nom_nom_days and month_data.nom_nom_days > 0) else days_with_meals
        avg_per_day = (purely_food / active_days_count) if active_days_count > 0 else 0.0

        # Etc Expenses Total
        etc_total = sum(item.amount for item in month_data.expenses.etc)

        # Total Cash Damage
        cash_damage = (
            purely_food +
            etc_total +
            month_data.expenses.rental +
            month_data.expenses.utilities +
            month_data.expenses.petrol
        )

        return MonthAnalytics(
            purely_food_expenses=round(purely_food, 2),
            breakfast_total=round(breakfast_total, 2),
            breakfast_count=breakfast_count,
            breakfast_average=round(avg_breakfast, 2),
            lunch_total=round(lunch_total, 2),
            lunch_count=lunch_count,
            lunch_average=round(avg_lunch, 2),
            dinner_total=round(dinner_total, 2),
            dinner_count=dinner_count,
            dinner_average=round(avg_dinner, 2),
            average_cost_per_day=round(avg_per_day, 2),
            etc_expenses_total=round(etc_total, 2),
            total_cash_damage=round(cash_damage, 2),
            chart_labels=chart_labels,
            chart_daily_costs=chart_daily_costs,
            chart_breakfast_costs=chart_breakfast_costs,
            chart_lunch_costs=chart_lunch_costs,
            chart_dinner_costs=chart_dinner_costs,
        )

    def _format_day_label(self, date_str: str, day_of_week: str) -> str:
        """Formats '2026-07-01' and 'Wednesday' to '01 (Wed)'."""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            day_num = f"{dt.day:02d}"
            short_dow = dt.strftime("%a")
            return f"{day_num} ({short_dow})"
        except ValueError:
            short_dow = day_of_week[:3] if len(day_of_week) >= 3 else day_of_week
            day_part = date_str.split("-")[-1]
            return f"{day_part} ({short_dow})"
