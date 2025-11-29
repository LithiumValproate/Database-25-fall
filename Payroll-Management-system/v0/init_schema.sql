create schema payroll_management;

use payroll_management;

create table Employee
(
    EmployeeId     char(8)        not null auto_increment comment '员工编号',
    EmployeeName   varchar(20)    not null comment '姓名',
    Department     varchar(30)    not null comment '部门',
    Position       varchar(30)    not null comment '职位',
    BasicSalary    decimal(10, 2) not null comment '基本工资',
    JoinDate       date           not null comment '入职日期',
    Contact        varchar(50) comment '联系方式',
    PaymentAccount varchar(50) comment '工资支付账户',
    primary key (EmployeeId)
) comment '员工';

create table Payroll_Items
(
    ItemId   char(4)     not null comment '项目编号',
    ItemName varchar(20) not null unique comment '项目名称',
    ItemRule text        not null comment '计算规则描述',
    ItemType bool        not null comment '项目类型，0表示扣除项目，1表示奖励项目',
    primary key (ItemId)
) comment '工资奖励/扣除项目';

create table Bonus_Record
(
    BonusId     char(14)      not null auto_increment comment '记录编号',
    EmployeeId  char(8)       not null comment '员工编号',
    BonusType   char(4)       not null comment '奖金类型',
    BonusAmount decimal(8, 2) not null comment '金额',
    BonusDate   date comment '发放日期',
    primary key (BonusId),
    foreign key (EmployeeId) references Employee (EmployeeId),
    foreign key (BonusType) references Payroll_Items (ItemId)
) comment '奖金记录';

create trigger trg_Bonus_type
    before insert
    on Bonus_Record
    for each row
begin
    declare v_type bool;
    select ItemType into v_type from Payroll_Items where ItemId = new.BonusType;
    if v_type = 0 then
        signal sqlstate '45000' set message_text = 'BonusType must refer to a reward item';
    end if;
end;

create table Deduction_Record
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

create trigger trg_Deduction_type
    before insert
    on Deduction_Record
    for each row
begin
    declare v_type bool;
    select ItemType into v_type from Payroll_Items where ItemId = new.DeductionType;
    if v_type = 1 then
        signal sqlstate '45000' set message_text = 'DeductionType must refer to a deduction item';
    end if;
end;

create procedure checkDateRange(in s date, in e date)
begin
    if e < s then
        signal sqlstate '45000'
            set message_text = 'EndDate must be >= StartDate';
    end if;
end;

create table Absence_Type
(
    AbsenceType varchar(20) not null comment '缺勤类型',
    Description varchar(200) comment '描述',
    primary key (AbsenceType)
) comment '缺勤类型';

create table Absence_Record
(
    AbsenceId   char(10)     not null auto_increment comment '记录编号',
    EmployeeId  char(8)      not null comment '员工编号',
    AbsenceType varchar(20)  not null comment '缺勤类型',
    StartDate   date         not null comment '开始日期',
    EndDate     date         not null comment '结束日期',
    Duration    int unsigned not null comment '缺勤天数',
    Attachment  text comment '证明材料',
    primary key (AbsenceId),
    foreign key (EmployeeId) references Employee (EmployeeId),
    foreign key (AbsenceType) references Absence_Type (AbsenceType)
) comment '缺勤记录';

create trigger trg_Absence_date
    before insert
    on Absence_Record
    for each row
begin
    call checkDateRange(new.StartDate, new.EndDate);
end;

create table Overtime_Record
(
    OvertimeId char(10)     not null auto_increment comment '记录编号',
    EmployeeId char(8)      not null comment '员工编号',
    StartDate  date         not null comment '加班开始时间',
    EndDate    date         not null comment '加班结束时间',
    Duration   int unsigned not null comment '加班时长',
    Attachment text comment '证明材料',
    primary key (OvertimeId),
    foreign key (EmployeeId) references Employee (EmployeeId)
) comment '加班记录';

create trigger trg_Overtime_date
    before insert
    on Overtime_Record
    for each row
begin
    call checkDateRange(new.StartDate, new.EndDate);
end;