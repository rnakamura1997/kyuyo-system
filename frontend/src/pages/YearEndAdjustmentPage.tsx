/** 年末調整ページ */

import React from "react";
import { Box, Typography } from "@mui/material";

export default function YearEndAdjustmentPage() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        年末調整
      </Typography>
      <Typography variant="body1" color="text.secondary">
        年末調整の処理を行います。各種控除の入力・計算・帳票出力が行えます。
      </Typography>
    </Box>
  );
}
