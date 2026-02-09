/** 会社一覧ページ */

import React from "react";
import { Box, Typography } from "@mui/material";

export default function CompaniesPage() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        会社一覧
      </Typography>
      <Typography variant="body1" color="text.secondary">
        登録されている会社の一覧を表示します。会社の追加・編集・削除が行えます。
      </Typography>
    </Box>
  );
}
