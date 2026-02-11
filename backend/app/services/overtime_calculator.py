"""時間外・割増賃金計算サービス"""
import math
from dataclasses import dataclass


@dataclass
class OvertimeResult:
    """割増賃金計算結果"""
    overtime_statutory_pay: int = 0         # 法定時間外手当（25%）
    overtime_within_statutory_pay: int = 0  # 法定内残業手当
    night_pay: int = 0                      # 深夜手当（25%）
    statutory_holiday_pay: int = 0          # 法定休日手当（35%）
    non_statutory_holiday_pay: int = 0      # 所定休日手当
    over60h_premium_pay: int = 0            # 月60時間超割増（50%）
    night_overtime_pay: int = 0             # 深夜残業手当（50%）
    night_holiday_pay: int = 0              # 深夜休日手当（60%）
    night_overtime_holiday_pay: int = 0     # 深夜時間外休日手当
    total_overtime_pay: int = 0             # 合計


class OvertimeCalculator:
    # 割増率
    STATUTORY_OVERTIME_RATE = 0.25      # 法定時間外 25%
    NIGHT_RATE = 0.25                   # 深夜 25%
    STATUTORY_HOLIDAY_RATE = 0.35       # 法定休日 35%
    OVER_60H_RATE = 0.50               # 月60時間超 50%
    NIGHT_OVERTIME_RATE = 0.50          # 深夜+残業 50%
    NIGHT_HOLIDAY_RATE = 0.60           # 深夜+休日 60%
    MONTHLY_OVERTIME_THRESHOLD = 3600   # 月60時間 = 3600分

    def calculate(
        self,
        base_hourly_rate: int,
        attendance: dict,
    ) -> OvertimeResult:
        """割増賃金を計算する

        Args:
            base_hourly_rate: 基礎時給（円）
            attendance: 勤怠データ（分単位フィールド）

        Returns:
            OvertimeResult
        """
        result = OvertimeResult()
        rate = base_hourly_rate / 60  # 分単位のレート

        # 法定内残業（割増なし、通常賃金のみ）
        within_statutory = attendance.get("overtime_within_statutory_minutes", 0)
        result.overtime_within_statutory_pay = math.floor(rate * within_statutory)

        # 法定時間外
        statutory_minutes = attendance.get("overtime_statutory_minutes", 0)

        # 60時間超の判定
        over_60h_minutes = max(0, statutory_minutes - self.MONTHLY_OVERTIME_THRESHOLD)
        normal_overtime_minutes = statutory_minutes - over_60h_minutes

        result.overtime_statutory_pay = math.floor(
            rate * normal_overtime_minutes * (1 + self.STATUTORY_OVERTIME_RATE)
        )
        result.over60h_premium_pay = math.floor(
            rate * over_60h_minutes * (1 + self.OVER_60H_RATE)
        )

        # 深夜手当
        night_minutes = attendance.get("night_minutes", 0)
        result.night_pay = math.floor(rate * night_minutes * self.NIGHT_RATE)

        # 法定休日
        statutory_holiday = attendance.get("statutory_holiday_minutes", 0)
        result.statutory_holiday_pay = math.floor(
            rate * statutory_holiday * (1 + self.STATUTORY_HOLIDAY_RATE)
        )

        # 所定休日（割増なし、通常賃金）
        non_statutory_holiday = attendance.get("non_statutory_holiday_minutes", 0)
        result.non_statutory_holiday_pay = math.floor(rate * non_statutory_holiday)

        # 深夜残業（深夜25% + 時間外25% = 50%）
        night_overtime = attendance.get("night_overtime_minutes", 0)
        result.night_overtime_pay = math.floor(
            rate * night_overtime * self.NIGHT_OVERTIME_RATE
        )

        # 深夜休日（深夜25% + 休日35% = 60%）
        night_holiday = attendance.get("night_holiday_minutes", 0)
        result.night_holiday_pay = math.floor(
            rate * night_holiday * self.NIGHT_HOLIDAY_RATE
        )

        # 深夜時間外休日
        night_overtime_holiday = attendance.get("night_overtime_holiday_minutes", 0)
        result.night_overtime_holiday_pay = math.floor(
            rate * night_overtime_holiday * (self.NIGHT_RATE + self.STATUTORY_HOLIDAY_RATE + self.STATUTORY_OVERTIME_RATE)
        )

        # 合計
        result.total_overtime_pay = (
            result.overtime_within_statutory_pay
            + result.overtime_statutory_pay
            + result.over60h_premium_pay
            + result.night_pay
            + result.statutory_holiday_pay
            + result.non_statutory_holiday_pay
            + result.night_overtime_pay
            + result.night_holiday_pay
            + result.night_overtime_holiday_pay
        )

        return result
