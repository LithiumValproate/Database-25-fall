insert into payroll_management.Payment_Method (PaymentMethodId, PaymentMethodName, Description, BankAccount) values ('ACC', 'Account Deposit', '内部账户结算方式，常用于公司内部报销', 'ACCT-019283');
insert into payroll_management.Payment_Method (PaymentMethodId, PaymentMethodName, Description, BankAccount) values ('CAS', 'Cash', '现场现金或备用金支付', null);
insert into payroll_management.Payment_Method (PaymentMethodId, PaymentMethodName, Description, BankAccount) values ('CHK', 'Cheque', '支票支付（少用方式）', 'CH-11203');
insert into payroll_management.Payment_Method (PaymentMethodId, PaymentMethodName, Description, BankAccount) values ('CRD', 'Credit Card', '通过公司或员工信用卡支付', '****');
insert into payroll_management.Payment_Method (PaymentMethodId, PaymentMethodName, Description, BankAccount) values ('DCT', 'Direct Debit', '从员工指定账户直接扣款', 'CCB-9988-371-22');
insert into payroll_management.Payment_Method (PaymentMethodId, PaymentMethodName, Description, BankAccount) values ('MOB', 'Mobile Pay', '使用手机钱包如PayPay/LinePay等', 'TG-889922');
insert into payroll_management.Payment_Method (PaymentMethodId, PaymentMethodName, Description, BankAccount) values ('PAY', 'Payroll Auto', '工资系统内置自动发放机制（无需额外账户）', null);
insert into payroll_management.Payment_Method (PaymentMethodId, PaymentMethodName, Description, BankAccount) values ('TRF', 'Bank Transfer', '通过员工登记的银行账户进行转账', 'JP-0001-001-556');
