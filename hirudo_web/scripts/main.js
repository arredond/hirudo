import * as bloodPoints from './blood_points.js';
import * as bloodMap from './blood_map.js';
import * as datePicker from './date_picker.js';

let fixedPoints = [];
let mobilePoints = [];

async function main() {
    // Setup map
    bloodMap.setupMap();
    
    // Get selected day or today
    let selectedDay = window.location.hash.substring(1).split("-")
    let today = new Date();

    let [day, month] = selectedDay.length > 1 ? selectedDay : [today.getDate(), today.getMonth() + 1];

    datePicker.populateDatePicker(day, month);
    
    // Fetch data
    fixedPoints = await bloodPoints.retrieveFixedBloodPoints();
    
    let filterDate = `${day}/${month}/${today.getFullYear()}`;
    
    mobilePoints = await bloodPoints.retrieveMobileBloodPointsForDate(filterDate);

    console.log(fixedPoints);
    console.log(mobilePoints);

    // Add points to map
    bloodMap.addBloodPoints(fixedPoints, true);
    bloodMap.addBloodPoints(mobilePoints, false)
}

async function onHashChanged() {
    // Update date picker
    let selectedDay = window.location.hash.substring(1).split("-");
    let today = new Date();

    let [day, month] = selectedDay.length > 1 ? selectedDay : [today.getDate(), today.getMonth() + 1];
    
    datePicker.updateSelectedDate(day, month);
    
    // Update map
    let filterDate = `${day}/${month}/${today.getFullYear()}`;
    mobilePoints = await bloodPoints.retrieveMobileBloodPointsForDate(filterDate);
    
    console.log(mobilePoints?.features);
    
    bloodMap.clearMarkers();
    bloodMap.addBloodPoints(mobilePoints, false)
}

window.onload = main;
window.onhashchange = onHashChanged;