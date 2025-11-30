-- v2 --

drop schema if exists payroll_management;
create schema payroll_management;
use payroll_management;

create table Employee
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

create table Event
(
    EventId     char(4)     not null comment '事件类型编号',
    EventName   varchar(20) not null unique comment '事件类型',
    EventType   bool        not null comment '事件类别，0表示缺勤，1表示加班',
    Description varchar(200) comment '描述',
    primary key (EventId)
) comment '工作事件类型';

create table Absence_Record
(
    AbsenceId     char(10)     not null comment '记录编号',
    EmployeeId    char(8)      not null comment '员工编号',
    AbsenceType   char(4)      not null comment '缺勤类型编号',
    StartDateTime datetime     not null comment '开始时间',
    EndDateTime   datetime     not null comment '结束时间',
    Duration      int unsigned not null comment '缺勤时长（分钟）',
    Attachment    mediumtext comment '证明材料',
    primary key (AbsenceId),
    foreign key (EmployeeId) references Employee (EmployeeId),
    foreign key (AbsenceType) references Event (EventId)
) comment '缺勤记录';

create table Overtime_Record
(
    OvertimeId    char(10)     not null comment '记录编号',
    EmployeeId    char(8)      not null comment '员工编号',
    OvertimeType  char(4)      not null comment '加班类型编号',
    StartDateTime datetime     not null comment '加班开始时间',
    EndDateTime   datetime     not null comment '加班结束时间',
    Duration      int unsigned not null comment '加班时长（分钟）',
    Attachment    mediumtext comment '证明材料',
    primary key (OvertimeId),
    foreign key (EmployeeId) references Employee (EmployeeId),
    foreign key (OvertimeType) references Event (EventId)
) comment '加班记录';

create table Payroll_Item
(
    ItemId   char(6)     not null comment '项目编号',
    ItemName varchar(20) not null unique comment '项目名称',
    ItemType bool        not null comment '项目类型，0表示扣除项目，1表示奖励项目',
    ItemRule text        not null comment '计算规则描述',
    primary key (ItemId)
) comment '工资奖励/扣除项目';

create table Bonus_Record
(
    BonusId     char(14)      not null comment '记录编号',
    EmployeeId  char(8)       not null comment '员工编号',
    BonusType   char(6)       not null comment '奖金类型',
    BonusAmount decimal(8, 2) not null comment '金额',
    BonusDate   date comment '发放日期',
    IsSettled   bool          not null default 0 comment '是否已发放',
    primary key (BonusId),
    foreign key (EmployeeId) references Employee (EmployeeId),
    foreign key (BonusType) references Payroll_Item (ItemId)
) comment '奖金记录';

create table Deduction_Record
(
    DeductionId     char(14)      not null comment '扣款记录编号',
    EmployeeId      char(8)       not null comment '员工编号',
    DeductionType   char(6)       not null comment '扣款类型',
    DeductionAmount decimal(8, 2) not null comment '扣款金额',
    DeductionDate   date comment '扣款日期',
    IsSettled       bool          not null default 0 comment '是否已扣款',
    primary key (DeductionId),
    foreign key (EmployeeId) references Employee (EmployeeId),
    foreign key (DeductionType) references Payroll_Item (ItemId)
) comment '扣款记录';

create table Event_to_Payroll_Item
(
    MapId    int     not null auto_increment comment '映射编号',
    ItemId   char(6) not null comment '项目编号',
    EventId  char(4) not null comment '事件编号',
    IsActive bool    not null comment '是否启用',
    primary key (MapId),
    unique (ItemId, EventId),
    foreign key (ItemId) references Payroll_Item (ItemId),
    foreign key (EventId) references Event (EventId)
) comment '工资项目/工作事件映射';

create table Payment_Method
(
    PaymentMethodId   char(3)     not null comment '支付方式编号',
    PaymentMethodName varchar(20) not null unique comment '支付方式名称',
    Description       varchar(200) comment '描述',
    BankAccount       varchar(50) comment '银行账户信息',
    primary key (PaymentMethodId)
) comment '支付方式';

create table Payroll_Record
(
    PayrollId      char(14)       not null comment '工资单编号',
    EmployeeId     char(8)        not null comment '员工编号',
    PayrollDate    date           not null comment '发放日期',
    PaymentMethod  char(3)        not null comment '支付方式',
    BasicSalary    decimal(10, 2) not null comment '基本工资',
    TotalBonus     decimal(10, 2) not null comment '总奖金',
    TotalDeduction decimal(10, 2) not null comment '总扣款',
    NetSalary      decimal(10, 2) not null comment '实发工资',
    primary key (PayrollId),
    foreign key (EmployeeId) references Employee (EmployeeId),
    foreign key (PaymentMethod) references Payment_Method (PaymentMethodId)
) comment '工资单记录';


delimiter $$
create procedure checkDateTimeRange(
    in s datetime,
    in e datetime
)
begin
    if e <= s then
        signal sqlstate '45000'
            set message_text = 'EndDateTime must be > StartDateTime';
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

create trigger trg_Absence_type
    before insert
    on Absence_Record
    for each row
begin
    if (select EventType from Event where EventId = new.AbsenceType) = 1 then
        signal sqlstate '45000' set message_text = 'AbsenceType must refer to an absence event';
    end if;
end $$

create trigger trg_Overtime_type
    before insert
    on Overtime_Record
    for each row
begin
    if (select EventType from Event where EventId = new.OvertimeType) = 0 then
        signal sqlstate '45000' set message_text = 'OvertimeType must refer to an overtime event';
    end if;
end $$

create trigger trg_Absence_calc
    before insert
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

create trigger trg_Bonus_type
    before insert
    on Bonus_Record
    for each row
begin
    if (select ItemType from Payroll_Item where ItemId = new.BonusType) = 0 then
        signal sqlstate '45000' set message_text = 'BonusType must refer to a reward item';
    end if;
end $$

create trigger trg_Deduction_type
    before insert
    on Deduction_Record
    for each row
begin
    if (select ItemType from Payroll_Item where ItemId = new.DeductionType) = 1 then
        signal sqlstate '45000' set message_text = 'DeductionType must refer to a deduction item';
    end if;
end $$

create trigger trg_Bonus_default_date
    before insert
    on Bonus_Record
    for each row
begin
    if new.BonusDate is null then
        set new.BonusDate = date_format(curdate(), '%Y-%m-28');
    end if;
end $$

create trigger trg_Deduction_default_date
    before insert
    on Deduction_Record
    for each row
begin
    if new.DeductionDate is null then
        set new.DeductionDate = date_format(curdate(), '%Y-%m-28');
    end if;
end $$

create trigger trg_Absence_type_update
    before update
    on Absence_Record
    for each row
begin
    if (select EventType from Event where EventId = new.AbsenceType) = 1 then
        signal sqlstate '45000' set message_text = 'AbsenceType must refer to an absence event';
    end if;
end $$

create trigger trg_Absence_calc_update
    before update
    on Absence_Record
    for each row
begin
    call checkDateTimeRange(new.StartDateTime, new.EndDateTime);
    set new.Duration = calcDuration(new.StartDateTime, new.EndDateTime);
end $$

create trigger trg_Overtime_type_update
    before update
    on Overtime_Record
    for each row
begin
    if (select EventType from Event where EventId = new.OvertimeType) = 0 then
        signal sqlstate '45000' set message_text = 'OvertimeType must refer to an overtime event';
    end if;
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