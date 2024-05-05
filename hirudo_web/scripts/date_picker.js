const classNameSelected = "selected";
const classNameIdle = "idle";
const monthNames = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
let dateIds = []

export function populateDatePicker(selectedDay, selectedMonth) {
    let datePickerView = document.getElementById('date-picker');

    let itemDate = new Date();

    for (let i = 0; i < 7; i++) {
        let [itemDay, itemMonth] = [itemDate.getDate(), itemDate.getMonth() + 1];
        let isSelected = itemDay === parseInt(selectedDay) && itemMonth === parseInt(selectedMonth);
        let dateItemView = buildDateItemView(itemDay, itemMonth, isSelected);
        datePickerView.appendChild(dateItemView);

        itemDate.setDate(itemDate.getDate() + 1);
    }

    dateIds = Array.from(datePickerView.children).map((item) => item.id);
}

export function updateSelectedDate(day, month) {
    let selectedId = getIdForDate(day, month);

    let datePickerView = document.getElementById('date-picker');
    let dateItems = datePickerView.children;

    for (let i = 0; i < dateItems.length; i++) {
        dateItems[i].className = dateItems[i].id === selectedId ? classNameSelected : classNameIdle;
    }
}

function buildDateItemView(day, month, isSelected) {
    let id = getIdForDate(day, month);
    let className = isSelected ? classNameSelected : classNameIdle;
    let dateItemView = document.createElement('a');
    dateItemView.id = id;
    dateItemView.className = className;
    dateItemView.href = `#${day}-${month}`;

    dateItemView.innerHTML = `
        <div class="month">${monthNames[month - 1]}</div>
        <div class="day">${day}</div>
    `;

    return dateItemView;
}


function getIdForDate(day, month) {
    return `date-picker-item-${day}-${month}`;
}