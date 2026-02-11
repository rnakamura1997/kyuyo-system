import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Paper, Typography, Button, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, Snackbar, Alert,
  CircularProgress, MenuItem, Select, FormControl, InputLabel, IconButton,
} from '@mui/material';
import { PlayArrow, Check, Cancel, PictureAsPdf, Refresh } from '@mui/icons-material';
import api from '@/services/api';

interface PayrollRecord {
  id: number;
  employee_id: number;
  version: number;
  status: string;
  payment_date: string;
  total_earnings: number;
  total_deductions: number;
  net_pay: number;
}

interface PayrollPeriod {
  id: number;
  year_month: number;
  period_type: string;
  status: string;
  payment_date: string;
}

const statusColor = (s: string) => {
  switch (s) {
    case 'draft': return 'warning';
    case 'confirmed': return 'success';
    case 'cancelled': return 'error';
    default: return 'default';
  }
};

const statusLabel = (s: string) => {
  switch (s) {
    case 'draft': return '下書き';
    case 'confirmed': return '確定';
    case 'cancelled': return '取消';
    default: return s;
  }
};

const fmt = (n: number) => n.toLocaleString('ja-JP');

const PayrollPage: React.FC = () => {
  const [periods, setPeriods] = useState<PayrollPeriod[]>([]);
  const [records, setRecords] = useState<PayrollRecord[]>([]);
  const [selectedPeriod, setSelectedPeriod] = useState<number | ''>('');
  const [loading, setLoading] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [cancelDialog, setCancelDialog] = useState<{ open: boolean; recordId: number | null }>({ open: false, recordId: null });
  const [cancelReason, setCancelReason] = useState('');
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({ open: false, message: '', severity: 'success' });

  const fetchPeriods = useCallback(async () => {
    try {
      const res = await api.get('/payroll-periods', { params: { limit: 50 } });
      setPeriods(res.data.items);
    } catch { /* ignore */ }
  }, []);

  const fetchRecords = useCallback(async () => {
    if (!selectedPeriod) return;
    setLoading(true);
    try {
      const res = await api.get('/payroll/records', { params: { payroll_period_id: selectedPeriod, limit: 200 } });
      setRecords(res.data.items);
    } catch {
      setSnackbar({ open: true, message: 'データ取得に失敗しました', severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [selectedPeriod]);

  useEffect(() => { fetchPeriods(); }, [fetchPeriods]);
  useEffect(() => { fetchRecords(); }, [fetchRecords]);

  const handleCalculate = async () => {
    if (!selectedPeriod) return;
    setCalculating(true);
    try {
      await api.post('/payroll/calculate', { payroll_period_id: selectedPeriod });
      setSnackbar({ open: true, message: '給与計算が完了しました', severity: 'success' });
      fetchRecords();
    } catch {
      setSnackbar({ open: true, message: '給与計算に失敗しました', severity: 'error' });
    } finally {
      setCalculating(false);
    }
  };

  const handleConfirm = async (id: number) => {
    try {
      await api.post(`/payroll/records/${id}/confirm`);
      setSnackbar({ open: true, message: '給与明細を確定しました', severity: 'success' });
      fetchRecords();
    } catch {
      setSnackbar({ open: true, message: '確定に失敗しました', severity: 'error' });
    }
  };

  const handleCancel = async () => {
    if (!cancelDialog.recordId) return;
    try {
      await api.post(`/payroll/records/${cancelDialog.recordId}/cancel`, { reason: cancelReason });
      setSnackbar({ open: true, message: '給与明細を取り消しました', severity: 'success' });
      setCancelDialog({ open: false, recordId: null });
      setCancelReason('');
      fetchRecords();
    } catch {
      setSnackbar({ open: true, message: '取消に失敗しました', severity: 'error' });
    }
  };

  const handlePdf = async (id: number) => {
    try {
      await api.post(`/payroll/records/${id}/pdf`);
      setSnackbar({ open: true, message: 'PDFを生成しました', severity: 'success' });
    } catch {
      setSnackbar({ open: true, message: 'PDF生成に失敗しました', severity: 'error' });
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">給与計算</Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>給与期間</InputLabel>
            <Select value={selectedPeriod} label="給与期間" onChange={(e) => setSelectedPeriod(Number(e.target.value))}>
              {periods.map((p) => (
                <MenuItem key={p.id} value={p.id}>
                  {Math.floor(p.year_month / 100)}年{p.year_month % 100}月 ({p.period_type})
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button variant="outlined" startIcon={<Refresh />} onClick={fetchRecords}>更新</Button>
          <Button
            variant="contained" color="primary"
            startIcon={calculating ? <CircularProgress size={20} /> : <PlayArrow />}
            onClick={handleCalculate} disabled={!selectedPeriod || calculating}
          >
            給与計算実行
          </Button>
        </Box>
      </Box>

      <TableContainer component={Paper}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
        ) : (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>社員ID</TableCell>
                <TableCell>Ver</TableCell>
                <TableCell>ステータス</TableCell>
                <TableCell>支給日</TableCell>
                <TableCell align="right">支給額</TableCell>
                <TableCell align="right">控除額</TableCell>
                <TableCell align="right">差引支給額</TableCell>
                <TableCell align="center">操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {records.length === 0 ? (
                <TableRow><TableCell colSpan={9} align="center">データがありません</TableCell></TableRow>
              ) : records.map((r) => (
                <TableRow key={r.id}>
                  <TableCell>{r.id}</TableCell>
                  <TableCell>{r.employee_id}</TableCell>
                  <TableCell>{r.version}</TableCell>
                  <TableCell><Chip label={statusLabel(r.status)} color={statusColor(r.status) as any} size="small" /></TableCell>
                  <TableCell>{r.payment_date}</TableCell>
                  <TableCell align="right">¥{fmt(r.total_earnings)}</TableCell>
                  <TableCell align="right">¥{fmt(r.total_deductions)}</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>¥{fmt(r.net_pay)}</TableCell>
                  <TableCell align="center">
                    {r.status === 'draft' && (
                      <IconButton color="success" title="確定" onClick={() => handleConfirm(r.id)}><Check /></IconButton>
                    )}
                    {r.status === 'confirmed' && (
                      <IconButton color="error" title="取消" onClick={() => setCancelDialog({ open: true, recordId: r.id })}><Cancel /></IconButton>
                    )}
                    <IconButton color="primary" title="PDF" onClick={() => handlePdf(r.id)}><PictureAsPdf /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TableContainer>

      <Dialog open={cancelDialog.open} onClose={() => setCancelDialog({ open: false, recordId: null })}>
        <DialogTitle>給与明細取消</DialogTitle>
        <DialogContent>
          <TextField fullWidth label="取消理由" multiline rows={3} value={cancelReason} onChange={(e) => setCancelReason(e.target.value)} sx={{ mt: 1 }} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCancelDialog({ open: false, recordId: null })}>キャンセル</Button>
          <Button variant="contained" color="error" onClick={handleCancel}>取消実行</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={() => setSnackbar({ ...snackbar, open: false })}>
        <Alert severity={snackbar.severity}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default PayrollPage;
