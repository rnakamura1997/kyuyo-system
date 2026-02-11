import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Paper, Typography, Button, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow,
  Dialog, DialogTitle, DialogContent, DialogActions, Snackbar, Alert,
  CircularProgress, MenuItem, Select, FormControl, InputLabel,
} from '@mui/material';
import { Upload, Refresh } from '@mui/icons-material';
import api from '@/services/api';

interface AttendanceRecord {
  id: number;
  employee_id: number;
  year_month: number;
  work_days: number | null;
  absence_days: number;
  late_count: number;
  early_leave_count: number;
  total_work_minutes: number | null;
  regular_minutes: number | null;
  overtime_statutory_minutes: number;
  night_minutes: number;
  statutory_holiday_minutes: number;
}

const currentYearMonth = () => {
  const now = new Date();
  return now.getFullYear() * 100 + (now.getMonth() + 1);
};

const AttendancePage: React.FC = () => {
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [yearMonth, setYearMonth] = useState(currentYearMonth());
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({ open: false, message: '', severity: 'success' });
  const [importOpen, setImportOpen] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/attendance', { params: { year_month: yearMonth, limit: 200 } });
      setRecords(res.data.items);
    } catch {
      setSnackbar({ open: true, message: 'データの取得に失敗しました', severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [yearMonth]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('year_month', String(yearMonth));
    try {
      const res = await api.post('/attendance/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setSnackbar({ open: true, message: res.data.message, severity: 'success' });
      setImportOpen(false);
      fetchData();
    } catch {
      setSnackbar({ open: true, message: 'インポートに失敗しました', severity: 'error' });
    }
  };

  const formatHours = (minutes: number | null) => {
    if (minutes === null || minutes === undefined) return '-';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return `${h}:${String(m).padStart(2, '0')}`;
  };

  // Year-month options (last 12 months)
  const ymOptions: number[] = [];
  for (let i = 0; i < 12; i++) {
    const d = new Date();
    d.setMonth(d.getMonth() - i);
    ymOptions.push(d.getFullYear() * 100 + (d.getMonth() + 1));
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">勤怠データ管理</Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>対象年月</InputLabel>
            <Select value={yearMonth} label="対象年月" onChange={(e) => setYearMonth(Number(e.target.value))}>
              {ymOptions.map((ym) => (
                <MenuItem key={ym} value={ym}>{Math.floor(ym / 100)}年{ym % 100}月</MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button variant="outlined" startIcon={<Refresh />} onClick={fetchData}>更新</Button>
          <Button variant="contained" startIcon={<Upload />} onClick={() => setImportOpen(true)}>CSVインポート</Button>
        </Box>
      </Box>

      <TableContainer component={Paper}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>社員ID</TableCell>
                <TableCell align="right">出勤日数</TableCell>
                <TableCell align="right">欠勤日数</TableCell>
                <TableCell align="right">遅刻</TableCell>
                <TableCell align="right">早退</TableCell>
                <TableCell align="right">総労働時間</TableCell>
                <TableCell align="right">所定内</TableCell>
                <TableCell align="right">法定外残業</TableCell>
                <TableCell align="right">深夜</TableCell>
                <TableCell align="right">休日出勤</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {records.length === 0 ? (
                <TableRow><TableCell colSpan={10} align="center">データがありません</TableCell></TableRow>
              ) : (
                records.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell>{r.employee_id}</TableCell>
                    <TableCell align="right">{r.work_days ?? '-'}</TableCell>
                    <TableCell align="right">{r.absence_days}</TableCell>
                    <TableCell align="right">{r.late_count}</TableCell>
                    <TableCell align="right">{r.early_leave_count}</TableCell>
                    <TableCell align="right">{formatHours(r.total_work_minutes)}</TableCell>
                    <TableCell align="right">{formatHours(r.regular_minutes)}</TableCell>
                    <TableCell align="right">{formatHours(r.overtime_statutory_minutes)}</TableCell>
                    <TableCell align="right">{formatHours(r.night_minutes)}</TableCell>
                    <TableCell align="right">{formatHours(r.statutory_holiday_minutes)}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </TableContainer>

      <Dialog open={importOpen} onClose={() => setImportOpen(false)}>
        <DialogTitle>CSVインポート</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            CSV形式の勤怠データファイルを選択してください。
          </Typography>
          <input type="file" accept=".csv" onChange={handleImport} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setImportOpen(false)}>キャンセル</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={() => setSnackbar({ ...snackbar, open: false })}>
        <Alert severity={snackbar.severity}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default AttendancePage;
