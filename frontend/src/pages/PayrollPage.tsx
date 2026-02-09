/** 給与計算ページ */

import React from "react";
import { Box, Typography } from "@mui/material";

export default function PayrollPage() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        給与計算
      </Typography>
      <Typography variant="body1" color="text.secondary">
        月次の給与計算を実行します。対象期間と対象者を選択して給与を計算できます。
      </Typography>
    </Box>
  );
}
