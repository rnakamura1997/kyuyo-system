/** 従業員管理ページ - CRUD（タブ付き編集ダイアログ） */

import React, { useState, useEffect, useCallback } from "react";
import {
  Box,
  Typography,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableContainer,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Paper,
  IconButton,
  Alert,
  Snackbar,
  CircularProgress,
  InputAdornment,
  MenuItem,
  Grid,
  Tabs,
  Tab,
  Chip,
  FormControlLabel,
  Checkbox,
  Divider,
} from "@mui/material";
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Search as SearchIcon,
} from "@mui/icons-material";
import { useForm, Controller } from "react-hook-form";
import api from "@/services/api";

/* ---------- 型定義 ---------- */
interface Employee {
  id: number;
  employee_code: string;
  last_name: string;
  first_name: string;
  last_name_kana: string;
  first_name_kana: string;
  email: string;
  phone: string;
  birth_date: string;
  gender: string;
  postal_code: string;
  address: string;
  hire_date: string;
  resignation_date: string | null;
  employment_type: string;
  department: string;
  position: string;
  salary_type: string;
  base_salary: number;
  hourly_rate: number;
  daily_rate: number;
  commuting_allowance: number;
  tax_category: string;
  dependents_count: number;
  spouse_deduction: boolean;
  health_insurance: boolean;
  pension_insurance: boolean;
  employment_insurance: boolean;
  resident_tax_monthly: number;
  bank_code: string;
  bank_name: string;
  branch_code: string;
  branch_name: string;
  account_type: string;
  account_number: string;
  account_holder: string;
  is_active: boolean;
}

interface EmployeeForm {
  employee_code: string;
  last_name: string;
  first_name: string;
  last_name_kana: string;
  first_name_kana: string;
  email: string;
  phone: string;
  birth_date: string;
  gender: string;
  postal_code: string;
  address: string;
  hire_date: string;
  resignation_date: string;
  employment_type: string;
  department: string;
  position: string;
  salary_type: string;
  base_salary: number;
  hourly_rate: number;
  daily_rate: number;
  commuting_allowance: number;
  tax_category: string;
  dependents_count: number;
  spouse_deduction: boolean;
  health_insurance: boolean;
  pension_insurance: boolean;
  employment_insurance: boolean;
  resident_tax_monthly: number;
  bank_code: string;
  bank_name: string;
  branch_code: string;
  branch_name: string;
  account_type: string;
  account_number: string;
  account_holder: string;
}

const defaultValues: EmployeeForm = {
  employee_code: "",
  last_name: "",
  first_name: "",
  last_name_kana: "",
  first_name_kana: "",
  email: "",
  phone: "",
  birth_date: "",
  gender: "male",
  postal_code: "",
  address: "",
  hire_date: "",
  resignation_date: "",
  employment_type: "regular",
  department: "",
  position: "",
  salary_type: "monthly",
  base_salary: 0,
  hourly_rate: 0,
  daily_rate: 0,
  commuting_allowance: 0,
  tax_category: "甲",
  dependents_count: 0,
  spouse_deduction: false,
  health_insurance: true,
  pension_insurance: true,
  employment_insurance: true,
  resident_tax_monthly: 0,
  bank_code: "",
  bank_name: "",
  branch_code: "",
  branch_name: "",
  account_type: "ordinary",
  account_number: "",
  account_holder: "",
};

/* ---------- TabPanel ---------- */
function TabPanel(props: { children: React.ReactNode; value: number; index: number }) {
  const { children, value, index } = props;
  return (
    <Box role="tabpanel" hidden={value !== index} sx={{ pt: 2 }}>
      {value === index && children}
    </Box>
  );
}

/* ---------- コンポーネント ---------- */
export default function EmployeesPage() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterSalary, setFilterSalary] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Employee | null>(null);
  const [tabIndex, setTabIndex] = useState(0);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error";
  }>({ open: false, message: "", severity: "success" });

  const {
    control,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<EmployeeForm>({ defaultValues });

  const salaryType = watch("salary_type");

  /* ---- データ取得 ---- */
  const fetchEmployees = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (search) params.search = search;
      if (filterType) params.employment_type = filterType;
      if (filterSalary) params.salary_type = filterSalary;
      const res = await api.get("/employees", { params });
      setEmployees(res.data.items ?? res.data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "取得に失敗しました";
      setSnackbar({ open: true, message: msg, severity: "error" });
    } finally {
      setLoading(false);
    }
  }, [search, filterType, filterSalary]);

  useEffect(() => {
    fetchEmployees();
  }, [fetchEmployees]);

  /* ---- ダイアログ操作 ---- */
  const openCreateDialog = () => {
    setEditingId(null);
    reset(defaultValues);
    setTabIndex(0);
    setDialogOpen(true);
  };

  const openEditDialog = (emp: Employee) => {
    setEditingId(emp.id);
    reset({
      employee_code: emp.employee_code,
      last_name: emp.last_name,
      first_name: emp.first_name,
      last_name_kana: emp.last_name_kana,
      first_name_kana: emp.first_name_kana,
      email: emp.email,
      phone: emp.phone,
      birth_date: emp.birth_date ?? "",
      gender: emp.gender,
      postal_code: emp.postal_code ?? "",
      address: emp.address ?? "",
      hire_date: emp.hire_date ?? "",
      resignation_date: emp.resignation_date ?? "",
      employment_type: emp.employment_type,
      department: emp.department ?? "",
      position: emp.position ?? "",
      salary_type: emp.salary_type,
      base_salary: emp.base_salary ?? 0,
      hourly_rate: emp.hourly_rate ?? 0,
      daily_rate: emp.daily_rate ?? 0,
      commuting_allowance: emp.commuting_allowance ?? 0,
      tax_category: emp.tax_category ?? "甲",
      dependents_count: emp.dependents_count ?? 0,
      spouse_deduction: emp.spouse_deduction ?? false,
      health_insurance: emp.health_insurance ?? true,
      pension_insurance: emp.pension_insurance ?? true,
      employment_insurance: emp.employment_insurance ?? true,
      resident_tax_monthly: emp.resident_tax_monthly ?? 0,
      bank_code: emp.bank_code ?? "",
      bank_name: emp.bank_name ?? "",
      branch_code: emp.branch_code ?? "",
      branch_name: emp.branch_name ?? "",
      account_type: emp.account_type ?? "ordinary",
      account_number: emp.account_number ?? "",
      account_holder: emp.account_holder ?? "",
    });
    setTabIndex(0);
    setDialogOpen(true);
  };

  /* ---- 保存 ---- */
  const onSubmit = async (data: EmployeeForm) => {
    try {
      const payload = {
        ...data,
        resignation_date: data.resignation_date || null,
      };
      if (editingId) {
        await api.put(`/employees/${editingId}`, payload);
        setSnackbar({ open: true, message: "従業員情報を更新しました", severity: "success" });
      } else {
        await api.post("/employees", payload);
        setSnackbar({ open: true, message: "従業員を登録しました", severity: "success" });
      }
      setDialogOpen(false);
      fetchEmployees();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "保存に失敗しました";
      setSnackbar({ open: true, message: msg, severity: "error" });
    }
  };

  /* ---- 削除 ---- */
  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/employees/${deleteTarget.id}`);
      setSnackbar({ open: true, message: "従業員を削除しました", severity: "success" });
      setDeleteTarget(null);
      fetchEmployees();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "削除に失敗しました";
      setSnackbar({ open: true, message: msg, severity: "error" });
    }
  };

  /* ---- フィルタ ---- */
  const filtered = employees.filter((e) => {
    const name = `${e.last_name}${e.first_name}`;
    const kana = `${e.last_name_kana}${e.first_name_kana}`;
    const matchSearch =
      !search ||
      name.includes(search) ||
      kana.includes(search) ||
      e.employee_code.includes(search) ||
      (e.department && e.department.includes(search));
    const matchType = !filterType || e.employment_type === filterType;
    const matchSalary = !filterSalary || e.salary_type === filterSalary;
    return matchSearch && matchType && matchSalary;
  });

  const empTypeLabel = (t: string) => {
    const map: Record<string, string> = {
      regular: "正社員",
      contract: "契約社員",
      part_time: "パート",
      temporary: "派遣",
    };
    return map[t] ?? t;
  };

  const salaryTypeLabel = (t: string) => {
    const map: Record<string, string> = {
      monthly: "月給",
      daily: "日給",
      hourly: "時給",
    };
    return map[t] ?? t;
  };

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Typography variant="h4">従業員管理</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreateDialog}>
          新規登録
        </Button>
      </Box>

      {/* 検索・フィルタ */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={4}>
            <TextField
              size="small"
              placeholder="氏名・社員番号・部署で検索..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              fullWidth
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <TextField
              size="small"
              select
              label="雇用形態"
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              fullWidth
            >
              <MenuItem value="">すべて</MenuItem>
              <MenuItem value="regular">正社員</MenuItem>
              <MenuItem value="contract">契約社員</MenuItem>
              <MenuItem value="part_time">パート</MenuItem>
              <MenuItem value="temporary">派遣</MenuItem>
            </TextField>
          </Grid>
          <Grid item xs={6} sm={3}>
            <TextField
              size="small"
              select
              label="給与形態"
              value={filterSalary}
              onChange={(e) => setFilterSalary(e.target.value)}
              fullWidth
            >
              <MenuItem value="">すべて</MenuItem>
              <MenuItem value="monthly">月給</MenuItem>
              <MenuItem value="daily">日給</MenuItem>
              <MenuItem value="hourly">時給</MenuItem>
            </TextField>
          </Grid>
        </Grid>
      </Paper>

      {/* テーブル */}
      <TableContainer component={Paper}>
        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>社員番号</TableCell>
                <TableCell>氏名</TableCell>
                <TableCell>カナ</TableCell>
                <TableCell>部署</TableCell>
                <TableCell>役職</TableCell>
                <TableCell>雇用形態</TableCell>
                <TableCell>給与形態</TableCell>
                <TableCell>状態</TableCell>
                <TableCell align="center">操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} align="center">
                    データがありません
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((emp) => (
                  <TableRow key={emp.id} hover>
                    <TableCell>{emp.employee_code}</TableCell>
                    <TableCell>
                      {emp.last_name} {emp.first_name}
                    </TableCell>
                    <TableCell>
                      {emp.last_name_kana} {emp.first_name_kana}
                    </TableCell>
                    <TableCell>{emp.department}</TableCell>
                    <TableCell>{emp.position}</TableCell>
                    <TableCell>
                      <Chip label={empTypeLabel(emp.employment_type)} size="small" />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={salaryTypeLabel(emp.salary_type)}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={emp.is_active ? "在籍" : "退職"}
                        size="small"
                        color={emp.is_active ? "success" : "default"}
                      />
                    </TableCell>
                    <TableCell align="center">
                      <IconButton size="small" color="primary" onClick={() => openEditDialog(emp)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" color="error" onClick={() => setDeleteTarget(emp)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </TableContainer>

      {/* 登録・編集ダイアログ */}
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{ sx: { minHeight: "70vh" } }}
      >
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogTitle>{editingId ? "従業員編集" : "従業員登録"}</DialogTitle>
          <DialogContent dividers>
            <Tabs
              value={tabIndex}
              onChange={(_, v) => setTabIndex(v)}
              variant="scrollable"
              scrollButtons="auto"
            >
              <Tab label="基本情報" />
              <Tab label="雇用情報" />
              <Tab label="給与設定" />
              <Tab label="税・保険" />
              <Tab label="振込先" />
            </Tabs>

            {/* Tab 0: 基本情報 */}
            <TabPanel value={tabIndex} index={0}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="employee_code"
                    control={control}
                    rules={{ required: "社員番号は必須です" }}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="社員番号"
                        fullWidth
                        required
                        error={!!errors.employee_code}
                        helperText={errors.employee_code?.message}
                      />
                    )}
                  />
                </Grid>
                <Grid item xs={6} sm={4}>
                  <Controller
                    name="last_name"
                    control={control}
                    rules={{ required: "姓は必須です" }}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="姓"
                        fullWidth
                        required
                        error={!!errors.last_name}
                        helperText={errors.last_name?.message}
                      />
                    )}
                  />
                </Grid>
                <Grid item xs={6} sm={4}>
                  <Controller
                    name="first_name"
                    control={control}
                    rules={{ required: "名は必須です" }}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="名"
                        fullWidth
                        required
                        error={!!errors.first_name}
                        helperText={errors.first_name?.message}
                      />
                    )}
                  />
                </Grid>
                <Grid item xs={6} sm={4}>
                  <Controller
                    name="last_name_kana"
                    control={control}
                    render={({ field }) => (
                      <TextField {...field} label="姓（カナ）" fullWidth />
                    )}
                  />
                </Grid>
                <Grid item xs={6} sm={4}>
                  <Controller
                    name="first_name_kana"
                    control={control}
                    render={({ field }) => (
                      <TextField {...field} label="名（カナ）" fullWidth />
                    )}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="email"
                    control={control}
                    render={({ field }) => (
                      <TextField {...field} label="メールアドレス" type="email" fullWidth />
                    )}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="phone"
                    control={control}
                    render={({ field }) => <TextField {...field} label="電話番号" fullWidth />}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="birth_date"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="生年月日"
                        type="date"
                        fullWidth
                        InputLabelProps={{ shrink: true }}
                      />
                    )}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="gender"
                    control={control}
                    render={({ field }) => (
                      <TextField {...field} label="性別" select fullWidth>
                        <MenuItem value="male">男性</MenuItem>
                        <MenuItem value="female">女性</MenuItem>
                        <MenuItem value="other">その他</MenuItem>
                      </TextField>
                    )}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="postal_code"
                    control={control}
                    render={({ field }) => <TextField {...field} label="郵便番号" fullWidth />}
                  />
                </Grid>
                <Grid item xs={12} sm={8}>
                  <Controller
                    name="address"
                    control={control}
                    render={({ field }) => <TextField {...field} label="住所" fullWidth />}
                  />
                </Grid>
              </Grid>
            </TabPanel>

            {/* Tab 1: 雇用情報 */}
            <TabPanel value={tabIndex} index={1}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Controller
                    name="hire_date"
                    control={control}
                    rules={{ required: "入社日は必須です" }}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="入社日"
                        type="date"
                        fullWidth
                        required
                        InputLabelProps={{ shrink: true }}
                        error={!!errors.hire_date}
                        helperText={errors.hire_date?.message}
                      />
                    )}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Controller
                    name="resignation_date"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="退職日"
                        type="date"
                        fullWidth
                        InputLabelProps={{ shrink: true }}
                      />
                    )}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="employment_type"
                    control={control}
                    render={({ field }) => (
                      <TextField {...field} label="雇用形態" select fullWidth>
                        <MenuItem value="regular">正社員</MenuItem>
                        <MenuItem value="contract">契約社員</MenuItem>
                        <MenuItem value="part_time">パート</MenuItem>
                        <MenuItem value="temporary">派遣</MenuItem>
                      </TextField>
                    )}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="department"
                    control={control}
                    render={({ field }) => <TextField {...field} label="部署" fullWidth />}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="position"
                    control={control}
                    render={({ field }) => <TextField {...field} label="役職" fullWidth />}
                  />
                </Grid>
              </Grid>
            </TabPanel>

            {/* Tab 2: 給与設定 */}
            <TabPanel value={tabIndex} index={2}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="salary_type"
                    control={control}
                    render={({ field }) => (
                      <TextField {...field} label="給与形態" select fullWidth>
                        <MenuItem value="monthly">月給</MenuItem>
                        <MenuItem value="daily">日給</MenuItem>
                        <MenuItem value="hourly">時給</MenuItem>
                      </TextField>
                    )}
                  />
                </Grid>
                {salaryType === "monthly" && (
                  <Grid item xs={12} sm={4}>
                    <Controller
                      name="base_salary"
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          label="基本給（月額）"
                          type="number"
                          fullWidth
                          InputProps={{
                            endAdornment: <InputAdornment position="end">円</InputAdornment>,
                          }}
                        />
                      )}
                    />
                  </Grid>
                )}
                {salaryType === "hourly" && (
                  <Grid item xs={12} sm={4}>
                    <Controller
                      name="hourly_rate"
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          label="時給"
                          type="number"
                          fullWidth
                          InputProps={{
                            endAdornment: <InputAdornment position="end">円</InputAdornment>,
                          }}
                        />
                      )}
                    />
                  </Grid>
                )}
                {salaryType === "daily" && (
                  <Grid item xs={12} sm={4}>
                    <Controller
                      name="daily_rate"
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          label="日給"
                          type="number"
                          fullWidth
                          InputProps={{
                            endAdornment: <InputAdornment position="end">円</InputAdornment>,
                          }}
                        />
                      )}
                    />
                  </Grid>
                )}
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="commuting_allowance"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="通勤手当"
                        type="number"
                        fullWidth
                        InputProps={{
                          endAdornment: <InputAdornment position="end">円</InputAdornment>,
                        }}
                      />
                    )}
                  />
                </Grid>
              </Grid>
            </TabPanel>

            {/* Tab 3: 税・保険 */}
            <TabPanel value={tabIndex} index={3}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="tax_category"
                    control={control}
                    render={({ field }) => (
                      <TextField {...field} label="税区分" select fullWidth>
                        <MenuItem value="甲">甲欄</MenuItem>
                        <MenuItem value="乙">乙欄</MenuItem>
                      </TextField>
                    )}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="dependents_count"
                    control={control}
                    render={({ field }) => (
                      <TextField {...field} label="扶養人数" type="number" fullWidth />
                    )}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="resident_tax_monthly"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="住民税（月額）"
                        type="number"
                        fullWidth
                        InputProps={{
                          endAdornment: <InputAdornment position="end">円</InputAdornment>,
                        }}
                      />
                    )}
                  />
                </Grid>
                <Grid item xs={12}>
                  <Divider sx={{ my: 1 }} />
                </Grid>
                <Grid item xs={12} sm={3}>
                  <Controller
                    name="spouse_deduction"
                    control={control}
                    render={({ field }) => (
                      <FormControlLabel
                        control={<Checkbox checked={field.value} onChange={field.onChange} />}
                        label="配偶者控除"
                      />
                    )}
                  />
                </Grid>
                <Grid item xs={12} sm={3}>
                  <Controller
                    name="health_insurance"
                    control={control}
                    render={({ field }) => (
                      <FormControlLabel
                        control={<Checkbox checked={field.value} onChange={field.onChange} />}
                        label="健康保険"
                      />
                    )}
                  />
                </Grid>
                <Grid item xs={12} sm={3}>
                  <Controller
                    name="pension_insurance"
                    control={control}
                    render={({ field }) => (
                      <FormControlLabel
                        control={<Checkbox checked={field.value} onChange={field.onChange} />}
                        label="厚生年金"
                      />
                    )}
                  />
                </Grid>
                <Grid item xs={12} sm={3}>
                  <Controller
                    name="employment_insurance"
                    control={control}
                    render={({ field }) => (
                      <FormControlLabel
                        control={<Checkbox checked={field.value} onChange={field.onChange} />}
                        label="雇用保険"
                      />
                    )}
                  />
                </Grid>
              </Grid>
            </TabPanel>

            {/* Tab 4: 振込先 */}
            <TabPanel value={tabIndex} index={4}>
              <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                  <Controller
                    name="bank_code"
                    control={control}
                    render={({ field }) => <TextField {...field} label="銀行コード" fullWidth />}
                  />
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Controller
                    name="bank_name"
                    control={control}
                    render={({ field }) => <TextField {...field} label="銀行名" fullWidth />}
                  />
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Controller
                    name="branch_code"
                    control={control}
                    render={({ field }) => <TextField {...field} label="支店コード" fullWidth />}
                  />
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Controller
                    name="branch_name"
                    control={control}
                    render={({ field }) => <TextField {...field} label="支店名" fullWidth />}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="account_type"
                    control={control}
                    render={({ field }) => (
                      <TextField {...field} label="口座種別" select fullWidth>
                        <MenuItem value="ordinary">普通</MenuItem>
                        <MenuItem value="checking">当座</MenuItem>
                        <MenuItem value="savings">貯蓄</MenuItem>
                      </TextField>
                    )}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="account_number"
                    control={control}
                    render={({ field }) => <TextField {...field} label="口座番号" fullWidth />}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Controller
                    name="account_holder"
                    control={control}
                    render={({ field }) => (
                      <TextField {...field} label="口座名義（カナ）" fullWidth />
                    )}
                  />
                </Grid>
              </Grid>
            </TabPanel>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialogOpen(false)}>キャンセル</Button>
            <Button type="submit" variant="contained" disabled={isSubmitting}>
              {isSubmitting ? <CircularProgress size={20} /> : "保存"}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* 削除確認 */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>削除確認</DialogTitle>
        <DialogContent>
          <Typography>
            「{deleteTarget?.last_name} {deleteTarget?.first_name}」（
            {deleteTarget?.employee_code}）を削除してもよろしいですか？
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>キャンセル</Button>
          <Button variant="contained" color="error" onClick={handleDelete}>
            削除
          </Button>
        </DialogActions>
      </Dialog>

      {/* スナックバー */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          severity={snackbar.severity}
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          variant="filled"
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
