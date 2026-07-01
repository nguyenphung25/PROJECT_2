export const parkingRows = [
  { stt: '01', plate: '30H-888.88', timeIn: '10:24 AM,\n24/10/2023', duration: '02 giờ 15\nphút', fee: '35,000đ', status: 'Đang\nĐỗ', tone: 'green' },
  { stt: '02', plate: '29A-555.55', timeIn: '09:15 AM,\n24/10/2023', duration: '03 giờ 24\nphút', fee: '50,000đ', status: 'Đang\nĐỗ', tone: 'green' },
  { stt: '03', plate: '15A-123.45', timeIn: '08:30 AM,\n24/10/2023', duration: '04 giờ 09\nphút', fee: '65,000đ', status: 'Chờ Ra', tone: 'yellow' },
  { stt: '04', plate: '51G-999.99', timeIn: '07:45 AM,\n24/10/2023', duration: '04 giờ 54\nphút', fee: '80,000đ', status: 'Đang\nĐỗ', tone: 'green' },
];

export const priceRows = [
  { stt: '01', type: 'Ô tô\n(4-7\nchỗ)', vehicle: 'car', shift: 'Sáng\n(6h-\n14h)', tone: 'blue', hourly: '25.000đ', session: '150.000đ', day: '250.000đ', month: '1.200.000đ' },
  { stt: '02', type: 'Xe\nmáy', vehicle: 'bike', shift: 'Chiều\n(14h-\n22h)', tone: 'blue', hourly: '5.000đ', session: '30.000đ', day: '50.000đ', month: '250.000đ' },
  { stt: '03', type: 'Xe\nđạp', vehicle: 'bicycle', shift: 'Cả\nngày', tone: 'gray', hourly: '2.000đ', session: '10.000đ', day: '20.000đ', month: '100.000đ' },
  { stt: '04', type: 'Xe\ntải\n(Dưới\n3.5t)', vehicle: 'truck', shift: 'Đêm\n(22h-\n5h)', tone: 'dark', hourly: '40.000đ', session: '300.000đ', day: '500.000đ', month: '2.500.000đ' },
];

export const recentRows = [
  { plate: '60U1-4632', vehicle: 'Motorbike', type: 'Standard', inTime: '14:32:05', outTime: '--:--', fee: '--', status: 'INSIDE' },
  { plate: '18A12345', vehicle: 'Sedan', type: 'Monthly', inTime: '13:15:22', outTime: '14:28:44', fee: 'Included', status: 'EXITED' },
  { plate: '64U1-3872', vehicle: 'Motorbike', type: 'Standard', inTime: '12:44:10', outTime: '--:--', fee: '--', status: 'INSIDE' },
];

export const activities = [
  { title: 'Xe vào: 30A-123.45', desc: 'Vừa xong • Lối vào A', tone: 'blue' },
  { title: 'Xe ra: 29C-678.90', desc: '15 phút trước • Lối ra B', tone: 'light' },
  { title: 'Thẻ không hợp lệ', desc: '1 giờ trước • Cổng nội bộ', tone: 'red' },
];

export const shortcuts = [
  { title: 'Quản Lý Giá xe', desc: 'Thiết lập khung giờ và đơn giá đỗ xe theo loại phương tiện.' },
  { title: 'Quản Lý Người dùng', desc: 'Phân quyền nhân viên, quản lý thẻ cư dân và khách hàng thân thiết.' },
  { title: 'Quản lý Ra/Vào', desc: 'Giám sát camera thực tế tại cổng và điều khiển rào chắn từ xa.' },
  { title: 'Báo cáo Thống kê', desc: 'Tổng hợp doanh thu, biểu đồ lưu lượng theo ngày/tuần/tháng.' },
];
