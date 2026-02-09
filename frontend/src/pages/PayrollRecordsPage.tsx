/** 給与明細一覧ページ */

import React from "react";
import { Box, Typography } from "@mui/material";

export default function PayrollRecordsPage() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        給与明細一覧
      </Typography>
      <Typography variant="body1" color="text.secondary">
        過去の給与明細の一覧を表示します。明細の検索・閲覧・印刷が行えます。
      </Typography>
    </Box>
  );
}
