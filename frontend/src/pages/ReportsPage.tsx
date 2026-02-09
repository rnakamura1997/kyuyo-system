/** 帳票・レポートページ */

import React from "react";
import { Box, Typography } from "@mui/material";

export default function ReportsPage() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        帳票・レポート
      </Typography>
      <Typography variant="body1" color="text.secondary">
        各種帳票やレポートを生成・出力します。給与台帳、源泉徴収票などの帳票を作成できます。
      </Typography>
    </Box>
  );
}
