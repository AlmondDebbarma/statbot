// Demo JavaScript file with intentional bugs for Statbot testing.
// Run: analyze demo_code.js

// Bug 1 (JS001): Using == instead of ===
function isAdmin(user) {
    if (user.role == "admin") {  // loose equality!
        return true;
    }
    return false;
}

// Bug 2 (JS002): var in loop closure — all handlers print 5
function createHandlers() {
    var handlers = [];
    for (var i = 0; i < 5; i++) {
        handlers.push(function() {
            console.log(i);
        });
    }
    return handlers;
}

// Bug 3 (JS003): Missing await on async function
async function fetchUserData(userId) {
    const response = fetch(`/api/users/${userId}`);  // forgot await!
    const data = response.json();  // calling .json() on a Promise object
    return data;
}

// Bug 4 (JS005): Unhandled promise rejection
function loadDashboard() {
    fetchUserData(123).then(function(data) {
        renderDashboard(data);
    });
    // No .catch() — if fetchUserData rejects, it crashes silently
}

// Bug 5 (JS004): this binding loss
class Timer {
    constructor() {
        this.seconds = 0;
    }

    start() {
        setInterval(this.tick, 1000);  // `this` will be undefined in tick()
    }

    tick() {
        this.seconds++;
        console.log("Elapsed:", this.seconds);
    }
}

// Bug 6: Off-by-one in array processing
function getLastThree(arr) {
    var result = [];
    for (var i = arr.length; i > arr.length - 3; i--) {
        result.push(arr[i]);  // arr[arr.length] is undefined!
    }
    return result;
}

module.exports = { isAdmin, createHandlers, fetchUserData, Timer, getLastThree };
