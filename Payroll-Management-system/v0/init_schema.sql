create schema if not exists payroll_management;
use payroll_management;

create table if not exists Employee
(
    EmployeeId     char(8)        not null comment '员工编号',
    EmployeeName   varchar(20)    not null comment '姓名',
    Department     varchar(30)    not null comment '部门',
    Position       varchar(30)    not null comment '职位',
    BasicSalary    decimal(10, 2) not null comment '基本工资',
    JoinDate       date           not null comment '入职日期',
    Contact        varchar(50) comment '联系方式',
    PaymentAccount varchar(50) comment '工资支付账户',
    primary key (EmployeeId)
) comment '员工';

create table if not exists Payroll_Items
(
    ItemId   char(4)     not null comment '项目编号',
    ItemName varchar(20) not null unique comment '项目名称',
    ItemRule text        not null comment '计算规则描述',
    ItemType bool        not null comment '项目类型，0表示扣除项目，1表示奖励项目',
    primary key (ItemId)
) comment '工资奖励/扣除项目';

create table if not exists Bonus_Record
(
    BonusId     char(14)      not null comment '记录编号',
    EmployeeId  char(8)       not null comment '员工编号',
    BonusType   char(4)       not null comment '奖金类型',
    BonusAmount decimal(8, 2) not null comment '金额',
    BonusDate   date comment '发放日期',
    primary key (BonusId),
    foreign key (EmployeeId) references Employee (EmployeeId),
    foreign key (BonusType) references Payroll_Items (ItemId)
) comment '奖金记录';

create table if not exists Deduction_Record
(
    DeductionId     char(14)      not null comment '扣款记录编号',
    EmployeeId      char(8)       not null comment '员工编号',
    DeductionType   char(4)       not null comment '扣款类型',
    DeductionAmount decimal(8, 2) not null comment '扣款金额',
    DeductionDate   date comment '扣款日期',
    primary key (DeductionId),
    foreign key (EmployeeId) references Employee (EmployeeId),
    foreign key (DeductionType) references Payroll_Items (ItemId)
) comment '扣款记录';

create table if not exists Absence_Type
(
    AbsenceType varchar(20) not null comment '缺勤类型',
    Description varchar(200) comment '描述',
    primary key (AbsenceType)
) comment '缺勤类型';

create table if not exists Absence_Record
(
    AbsenceId     char(10)     not null comment '记录编号',
    EmployeeId    char(8)      not null comment '员工编号',
    AbsenceType   varchar(20)  not null comment '缺勤类型',
    StartDateTime datetime     not null comment '开始时间',
    EndDateTime   datetime     not null comment '结束时间',
    Duration      int unsigned not null comment '缺勤时长（分钟）',
    Attachment    mediumtext comment '证明材料',
    primary key (AbsenceId),
    foreign key (EmployeeId) references Employee (EmployeeId),
    foreign key (AbsenceType) references Absence_Type (AbsenceType)
) comment '缺勤记录';

create table if not exists Overtime_Type
(
    OvertimeType varchar(20) not null comment '加班类型',
    Description  varchar(200) comment '描述',
    primary key (OvertimeType)
) comment '加班类型';

create table if not exists Overtime_Record
(
    OvertimeId    char(10)     not null comment '记录编号',
    EmployeeId    char(8)      not null comment '员工编号',
    OvertimeType  varchar(20)  not null comment '加班类型',
    StartDateTime datetime     not null comment '加班开始时间',
    EndDateTime   datetime     not null comment '加班结束时间',
    Duration      int unsigned not null comment '加班时长（分钟）',
    Attachment    mediumtext comment '证明材料',
    primary key (OvertimeId),
    foreign key (EmployeeId) references Employee (EmployeeId),
    foreign key (OvertimeType) references Overtime_Type (OvertimeType)
) comment '加班记录';

create table if not exists Payment_Method
(
    PaymentMethodId   char(4)     not null comment '支付方式编号',
    PaymentMethodName varchar(20) not null unique comment '支付方式名称',
    Description       varchar(200) comment '描述',
    BankAccount       varchar(50) comment '银行账户信息',
    primary key (PaymentMethodId)
) comment '支付方式';

create table if not exists Payroll_Record
(
    PayrollId      char(14)       not null comment '工资单编号',
    EmployeeId     char(8)        not null comment '员工编号',
    PayrollDate    date           not null comment '发放日期',
    PaymentMethod  char(4)        not null comment '支付方式',
    BasicSalary    decimal(10, 2) not null comment '基本工资',
    TotalBonus     decimal(10, 2) not null comment '总奖金',
    TotalDeduction decimal(10, 2) not null comment '总扣款',
    NetSalary      decimal(10, 2) not null comment '实发工资',
    primary key (PayrollId),
    foreign key (EmployeeId) references Employee (EmployeeId),
    foreign key (PaymentMethod) references Payment_Method (PaymentMethodId)
) comment '工资单记录';

drop trigger if exists trg_Bonus_type;
drop trigger if exists trg_Deduction_type;
drop procedure if exists checkDateTimeRange;
drop function if exists calcDuration;
drop trigger if exists trg_Absence_calc;
drop trigger if exists trg_Absence_calc_update;
drop trigger if exists trg_Overtime_calc;
drop trigger if exists trg_Overtime_calc_update;

delimiter $$
create trigger trg_Bonus_type
    before insert
    on Bonus_Record
    for each row
begin
    if (select ItemType from Payroll_Items where ItemId = new.BonusType) = 0 then
        signal sqlstate '45000' set message_text = 'BonusType must refer to a reward item';
    end if;
end $$

create trigger trg_Deduction_type
    before insert
    on Deduction_Record
    for each row
begin
    if (select ItemType from Payroll_Items where ItemId = new.DeductionType) = 1 then
        signal sqlstate '45000' set message_text = 'DeductionType must refer to a deduction item';
    end if;
end $$

create procedure checkDateTimeRange(
    in s datetime,
    in e datetime
)
begin
    if e < s then
        signal sqlstate '45000'
            set message_text = 'EndDateTime must be >= StartDateTime';
    end if;
end $$

create function calcDuration(
    s datetime,
    e datetime
)
    returns int
    deterministic
begin
    return timestampdiff(minute, s, e);
end $$

create trigger trg_Absence_calc
    before insert
    on Absence_Record
    for each row
begin
    call checkDateTimeRange(new.StartDateTime, new.EndDateTime);
    set new.Duration = calcDuration(new.StartDateTime, new.EndDateTime);
end $$

create trigger trg_Absence_calc_update
    before update
    on Absence_Record
    for each row
begin
    call checkDateTimeRange(new.StartDateTime, new.EndDateTime);
    set new.Duration = calcDuration(new.StartDateTime, new.EndDateTime);
end $$

create trigger trg_Overtime_calc
    before insert
    on Overtime_Record
    for each row
begin
    call checkDateTimeRange(new.StartDateTime, new.EndDateTime);
    set new.Duration = calcDuration(new.StartDateTime, new.EndDateTime);
end $$

create trigger trg_Overtime_calc_update
    before update
    on Overtime_Record
    for each row
begin
    call checkDateTimeRange(new.StartDateTime, new.EndDateTime);
    set new.Duration = calcDuration(new.StartDateTime, new.EndDateTime);
end $$
delimiter ;
