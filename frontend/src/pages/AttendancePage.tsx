/** 勤怠データページ */

import React from "react";
import { Box, Typography } from "@mui/material";

export default function AttendancePage() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        勤怠データ
      </Typography>
      <Typography variant="body1" color="text.secondary">
        従業員の勤怠データを表示します。勤怠情報の登録・確認・承認が行えます。
      </Typography>
    </Box>
  );
}
