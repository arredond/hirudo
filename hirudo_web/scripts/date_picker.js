import '../libs/dayjs/dayjs.js';

const classNameSelected = "selected";
const classNameIdle = "idle";
let dateIds = []

export function populateDatePicker(selectedDate) {
    let datePickerView = document.getElementById('date-picker');

    let itemDate = dayjs().locale('es');

    for (let i = 0; i < 7; i++) {
        let isSelected = itemDate.isSame(selectedDate, 'day');
        let dateItemView = buildDateItemView(itemDate, isSelected);
        datePickerView.appendChild(dateItemView);

        itemDate = itemDate.add(1, 'day');
    }

    dateIds = Array.from(datePickerView.children).map((item) => item.id);
}

export function updateSelectedDate(selectedDate) {
    let formattedDate = selectedDate.format('DD/MM/YYYY');
    let selectedId = getIdForDate(formattedDate);
    console.log('Selected ID: ' + selectedId);

    let datePickerView = document.getElementById('date-picker');
    let dateItems = datePickerView.children;

    for (let i = 0; i < dateItems.length; i++) {
        console.log('Item ID: ' + dateItems[i].id);
        dateItems[i].className = dateItems[i].id === selectedId ? classNameSelected : classNameIdle;
    }
}

function buildDateItemView(date, isSelected) {
    let formattedDate = date.format('DD/MM/YYYY');
    let id = getIdForDate(formattedDate);
    let className = isSelected ? classNameSelected : classNameIdle;
    let dateItemView = document.createElement('a');
    dateItemView.id = id;
    dateItemView.className = className;
    dateItemView.href = `#${formattedDate}`;

    dateItemView.innerHTML = `
        <div class="month">${date.format('MMM')}</div>
        <div class="day">${date.format('DD')}</div>
    `;

    return dateItemView;
}


function getIdForDate(formattedDate) {
    return `date-picker-item-${formattedDate}`;
}