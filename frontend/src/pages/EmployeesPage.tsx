/** 従業員一覧ページ */

import React from "react";
import { Box, Typography } from "@mui/material";

export default function EmployeesPage() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        従業員一覧
      </Typography>
      <Typography variant="body1" color="text.secondary">
        登録されている従業員の一覧を表示します。従業員情報の追加・編集・削除が行えます。
      </Typography>
    </Box>
  );
}
