-- Absence_Record --
insert into payroll_management.Absence_Record (AbsenceId, EmployeeId, AbsenceType, StartDateTime, EndDateTime, Duration,
                                               Attachment)
values ('AB24010001', '13833593', 'AB02', '2024-01-15 09:00:00', '2024-01-15 13:00:00', 0, null);

-- Overtime_Record --
insert into payroll_management.Overtime_Record (OvertimeId, EmployeeId, OvertimeType, StartDateTime, EndDateTime,
                                                Duration, Attachment)
values ('OT24020001', '52754012', 'OW01', '2024-02-20 18:00:00', '2024-02-20 21:40:00', 0, null);

-- Bonus_Record --
insert into payroll_management.Bonus_Record (BonusId, EmployeeId, BonusType, BonusAmount, BonusDate, IsSettled)
values ('BN917249149201', '52754012', 'WOT002', 500.00, '2024-02-28', 0);

-- Deduction_Record --
insert into payroll_management.Deduction_Record (DeductionId, EmployeeId, DeductionType, DeductionAmount, DeductionDate,
                                                 IsSettled)
values ('DN483726195301', '13833593', 'ILL001', 100.00, '2024-01-31', 0);

-- Payroll_Record --
insert into payroll_management.Payroll_Record
select 'PR20240113833593',
       e.EmployeeId,
       '2024-01-31',
       'CRD',
       e.BasicSalary,
       coalesce((select sum(BonusAmount)
                 from payroll_management.Bonus_Record br
                 where br.EmployeeId = e.EmployeeId
                   and br.BonusDate between '2024-01-01' and '2024-01-31'), 0)     as TotalBonus,
       coalesce((select sum(DeductionAmount)
                 from payroll_management.Deduction_Record dr
                 where dr.EmployeeId = e.EmployeeId
                   and dr.DeductionDate between '2024-01-01' and '2024-01-31'), 0) as TotalDeduction,
       e.BasicSalary +
       coalesce((select sum(BonusAmount)
                 from payroll_management.Bonus_Record br
                 where br.EmployeeId = e.EmployeeId
                   and br.BonusDate between '2024-01-01' and '2024-01-31'), 0) -
       coalesce((select sum(DeductionAmount)
                 from payroll_management.Deduction_Record dr
                 where dr.EmployeeId = e.EmployeeId
                   and dr.DeductionDate between '2024-01-01' and '2024-01-31'), 0) as NetSalary
from payroll_management.Employee e
where e.EmployeeId = '13833593';

insert into payroll_management.Payroll_Record
select 'PR20240252754012',
       e.EmployeeId,
       '2024-02-29',
       'TRF',
       e.BasicSalary,
       coalesce((select sum(BonusAmount)
                 from payroll_management.Bonus_Record br
                 where br.EmployeeId = e.EmployeeId
                   and br.BonusDate between '2024-02-01' and '2024-02-29'), 0)     as TotalBonus,
       coalesce((select sum(DeductionAmount)
                 from payroll_management.Deduction_Record dr
                 where dr.EmployeeId = e.EmployeeId
                   and dr.DeductionDate between '2024-02-01' and '2024-02-29'), 0) as TotalDeduction,
       e.BasicSalary +
       coalesce((select sum(BonusAmount)
                 from payroll_management.Bonus_Record br
                 where br.EmployeeId = e.EmployeeId
                   and br.BonusDate between '2024-02-01' and '2024-02-29'), 0) -
       coalesce((select sum(DeductionAmount)
                 from payroll_management.Deduction_Record dr
                 where dr.EmployeeId = e.EmployeeId
                   and dr.DeductionDate between '2024-02-01' and '2024-02-29'), 0) as NetSalary
from payroll_management.Employee e
where e.EmployeeId = '52754012';