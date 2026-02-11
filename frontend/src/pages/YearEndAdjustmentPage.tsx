import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Paper, Typography, Button, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, Snackbar, Alert,
  CircularProgress, MenuItem, Select, FormControl, InputLabel, Grid,
} from '@mui/material';
import { Add, Send, Check, Undo, Lock } from '@mui/icons-material';
import api from '@/services/api';

interface YearEndAdjustment {
  id: number;
  employee_id: number;
  target_year: number;
  status: string;
  basic_deduction: number;
  spouse_deduction: number;
  dependent_deduction: number;
  life_insurance_premium: number;
  earthquake_insurance_premium: number;
  housing_loan_deduction: number;
  adjustment_amount: number | null;
}

const statusMap: Record<string, { label: string; color: any }> = {
  draft: { label: '下書き', color: 'default' },
  submitted: { label: '提出済', color: 'info' },
  returned: { label: '差戻し', color: 'warning' },
  approved: { label: '承認済', color: 'primary' },
  confirmed: { label: '確定', color: 'success' },
};

const YearEndAdjustmentPage: React.FC = () => {
  const [adjustments, setAdjustments] = useState<YearEndAdjustment[]>([]);
  const [targetYear, setTargetYear] = useState(new Date().getFullYear());
  const [loading, setLoading] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editData, setEditData] = useState<any>({});
  const [returnDialog, setReturnDialog] = useState<{ open: boolean; id: number | null }>({ open: false, id: null });
  const [returnReason, setReturnReason] = useState('');
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({ open: false, message: '', severity: 'success' });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/year-end/adjustments', { params: { target_year: targetYear, limit: 200 } });
      setAdjustments(res.data.items);
    } catch { setSnackbar({ open: true, message: 'データ取得に失敗しました', severity: 'error' }); }
    setLoading(false);
  }, [targetYear]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCreate = async () => {
    try {
      await api.post('/year-end/adjustments', editData);
      setSnackbar({ open: true, message: '作成しました', severity: 'success' });
      setEditOpen(false);
      setEditData({});
      fetchData();
    } catch { setSnackbar({ open: true, message: '作成に失敗しました', severity: 'error' }); }
  };

  const handleAction = async (id: number, action: string, body?: any) => {
    try {
      await api.post(`/year-end/adjustments/${id}/${action}`, body || {});
      setSnackbar({ open: true, message: '処理が完了しました', severity: 'success' });
      fetchData();
    } catch { setSnackbar({ open: true, message: '処理に失敗しました', severity: 'error' }); }
  };

  const fmt = (n: number | null) => n !== null ? '¥' + n.toLocaleString('ja-JP') : '-';

  const years = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">年末調整</Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>対象年</InputLabel>
            <Select value={targetYear} label="対象年" onChange={(e) => setTargetYear(Number(e.target.value))}>
              {years.map((y) => <MenuItem key={y} value={y}>{y}年</MenuItem>)}
            </Select>
          </FormControl>
          <Button variant="contained" startIcon={<Add />} onClick={() => { setEditData({ target_year: targetYear }); setEditOpen(true); }}>
            新規作成
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
                <TableCell>対象年</TableCell>
                <TableCell>ステータス</TableCell>
                <TableCell align="right">基礎控除</TableCell>
                <TableCell align="right">配偶者控除</TableCell>
                <TableCell align="right">扶養控除</TableCell>
                <TableCell align="right">過不足額</TableCell>
                <TableCell align="center">操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {adjustments.length === 0 ? (
                <TableRow><TableCell colSpan={9} align="center">データがありません</TableCell></TableRow>
              ) : adjustments.map((a) => (
                <TableRow key={a.id}>
                  <TableCell>{a.id}</TableCell>
                  <TableCell>{a.employee_id}</TableCell>
                  <TableCell>{a.target_year}</TableCell>
                  <TableCell><Chip label={statusMap[a.status]?.label || a.status} color={statusMap[a.status]?.color} size="small" /></TableCell>
                  <TableCell align="right">{fmt(a.basic_deduction)}</TableCell>
                  <TableCell align="right">{fmt(a.spouse_deduction)}</TableCell>
                  <TableCell align="right">{fmt(a.dependent_deduction)}</TableCell>
                  <TableCell align="right">{fmt(a.adjustment_amount)}</TableCell>
                  <TableCell align="center">
                    {a.status === 'draft' && <Button size="small" startIcon={<Send />} onClick={() => handleAction(a.id, 'submit')}>提出</Button>}
                    {a.status === 'submitted' && (
                      <>
                        <Button size="small" color="success" startIcon={<Check />} onClick={() => handleAction(a.id, 'approve')}>承認</Button>
                        <Button size="small" color="warning" startIcon={<Undo />} onClick={() => { setReturnDialog({ open: true, id: a.id }); }}>差戻</Button>
                      </>
                    )}
                    {a.status === 'approved' && <Button size="small" color="primary" startIcon={<Lock />} onClick={() => handleAction(a.id, 'confirm')}>確定</Button>}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TableContainer>

      <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>年末調整 新規作成</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={6}><TextField fullWidth label="社員ID" type="number" value={editData.employee_id || ''} onChange={(e) => setEditData({ ...editData, employee_id: Number(e.target.value) })} /></Grid>
            <Grid item xs={6}><TextField fullWidth label="対象年" type="number" value={editData.target_year || ''} onChange={(e) => setEditData({ ...editData, target_year: Number(e.target.value) })} /></Grid>
            <Grid item xs={6}><TextField fullWidth label="基礎控除" type="number" value={editData.basic_deduction || 0} onChange={(e) => setEditData({ ...editData, basic_deduction: Number(e.target.value) })} /></Grid>
            <Grid item xs={6}><TextField fullWidth label="配偶者控除" type="number" value={editData.spouse_deduction || 0} onChange={(e) => setEditData({ ...editData, spouse_deduction: Number(e.target.value) })} /></Grid>
            <Grid item xs={6}><TextField fullWidth label="扶養控除" type="number" value={editData.dependent_deduction || 0} onChange={(e) => setEditData({ ...editData, dependent_deduction: Number(e.target.value) })} /></Grid>
            <Grid item xs={6}><TextField fullWidth label="生命保険料控除" type="number" value={editData.life_insurance_premium || 0} onChange={(e) => setEditData({ ...editData, life_insurance_premium: Number(e.target.value) })} /></Grid>
            <Grid item xs={6}><TextField fullWidth label="地震保険料控除" type="number" value={editData.earthquake_insurance_premium || 0} onChange={(e) => setEditData({ ...editData, earthquake_insurance_premium: Number(e.target.value) })} /></Grid>
            <Grid item xs={6}><TextField fullWidth label="住宅ローン控除" type="number" value={editData.housing_loan_deduction || 0} onChange={(e) => setEditData({ ...editData, housing_loan_deduction: Number(e.target.value) })} /></Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>キャンセル</Button>
          <Button variant="contained" onClick={handleCreate}>作成</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={returnDialog.open} onClose={() => setReturnDialog({ open: false, id: null })}>
        <DialogTitle>差戻し</DialogTitle>
        <DialogContent>
          <TextField fullWidth label="差戻し理由" multiline rows={3} value={returnReason} onChange={(e) => setReturnReason(e.target.value)} sx={{ mt: 1 }} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReturnDialog({ open: false, id: null })}>キャンセル</Button>
          <Button variant="contained" color="warning" onClick={() => { handleAction(returnDialog.id!, 'return', { reason: returnReason }); setReturnDialog({ open: false, id: null }); setReturnReason(''); }}>差戻し実行</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={() => setSnackbar({ ...snackbar, open: false })}>
        <Alert severity={snackbar.severity}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default YearEndAdjustmentPage;
