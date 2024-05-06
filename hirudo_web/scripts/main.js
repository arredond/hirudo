import * as bloodPoints from './blood_points.js';
import * as bloodMap from './blood_map.js';
import * as datePicker from './date_picker.js';
import '../libs/dayjs/dayjs.js';
import customParseFormat from '../libs/dayjs/customParseFormat/custom_parse_format.js'

let fixedPoints = [];
let mobilePoints = [];
dayjs.extend(customParseFormat);

async function main() {
    // Setup map
    bloodMap.setupMap();
    
    // Get selected day or today
    let selectedDate = getSelectedDate();

    datePicker.populateDatePicker(selectedDate);
    
    // Fetch data
    fixedPoints = await bloodPoints.retrieveFixedBloodPoints();
    
    let filterDate = selectedDate.format('DD/MM/YYYY');
    mobilePoints = await bloodPoints.retrieveMobileBloodPointsForDate(filterDate);

    console.log(fixedPoints);
    console.log(mobilePoints);

    // Add points to map
    bloodMap.addBloodPoints(fixedPoints, true);
    bloodMap.addBloodPoints(mobilePoints, false)
}

async function onHashChanged() {
    // Update date picker
    let selectedDate = getSelectedDate();
    
    datePicker.updateSelectedDate(selectedDate);
    
    // Update map
    let filterDate = selectedDate.format('DD/MM/YYYY');
    mobilePoints = await bloodPoints.retrieveMobileBloodPointsForDate(filterDate);
    
    console.log(mobilePoints?.features);
    
    bloodMap.clearMarkers();
    bloodMap.addBloodPoints(mobilePoints, false)
}

function getSelectedDate() {
    let selectedDay = window.location.hash.substring(1);
    let date = dayjs().locale('es');

    if (selectedDay.length > 1) {
        date = dayjs(selectedDay, 'DD/MM/YYYY').locale('es');
    }
    return date;
}

window.onload = main;
window.onhashchange = onHashChanged;