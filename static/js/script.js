let map;
let markers = {};
let currentUser = null;

function toggleButtons(loggedIn) {
    const reportCurrent = document.getElementById('report-current-location-button');
    const reportCenter = document.getElementById('report-map-center-button');
    const logoutBtn = document.getElementById('logout-button');
    const authBtn = document.querySelector('.g_id_signin');
    const message = document.getElementById('report-message');
    
    reportCurrent.disabled = !loggedIn;
    reportCenter.disabled = !loggedIn;
    
    if (loggedIn) {
        logoutBtn.style.display = 'block';
        if (authBtn) authBtn.style.display = 'none';
        message.textContent = '通報場所を選択してボタンを押してください。';
    } else {
        logoutBtn.style.display = 'none';
        if (authBtn) authBtn.style.display = 'block';
        message.textContent = 'サインインして通報を開始してください。';
    }
}

async function checkLoginStatus() {
    try {
        const response = await fetch('/check_login');
        const data = await response.json();
        currentUser = data.user_id;
        toggleButtons(data.logged_in);
        
        loadBearLocations();
    } catch (error) {
        console.error("Login status check failed:", error);
    }
}

async function handleCredentialResponse(response) {
    try {
        const res = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: response.credential })
        });
        if (res.ok) {
            checkLoginStatus();
        }
    } catch (error) {
        console.error("Login failed:", error);
    }
}
window.handleCredentialResponse = handleCredentialResponse;

async function handleLogout() {
    try {
        const res = await fetch('/logout', { method: 'POST' });
        if (res.ok) {
            toggleButtons(false);
            currentUser = null;
            loadBearLocations();
        }
    } catch (error) {
        console.error("Logout failed:", error);
    }
}

async function loadBearLocations() {
    try {
        const response = await fetch('/locations');
        const locations = await response.json();
        
        Object.values(markers).forEach(marker => map.removeLayer(marker));
        markers = {};

        locations.forEach(location => {
            addMarker(location);
        });
    } catch (error) {
        console.error('Error loading locations:', error);
    }
}

async function reportLocation(lat, lng) {
    const locationData = { lat: lat, lng: lng };
    const message = document.getElementById('report-message');
    
    try {
        const response = await fetch('/locations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(locationData)
        });
        
        if (response.ok) {
            const newLocation = await response.json();
            
            addMarker(newLocation);
            message.textContent = 'クマの発見を通報しました！';
            alert('クマの発見を通報しました！');
        } else {
            throw new Error('Failed to save location.');
        }
    } catch (error) {
        console.error('Error reporting location:', error);
        alert('通報に失敗しました。');
        message.textContent = '通報に失敗しました。';
    }
}

async function deleteBearLocation(locationId) {
    try {
        const response = await fetch(`/locations/${locationId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            const markerToDelete = markers[locationId];
            if (markerToDelete) {
                map.removeLayer(markerToDelete);
                delete markers[locationId];
            }

            const message = document.getElementById('report-message');
            message.textContent = '通報を削除しました。';
            alert('通報を削除しました。');
        } else if (response.status === 403) {
            alert('この通報はあなたのアカウントで登録されたものではありません。削除できません。');
        } else {
            throw new Error('Failed to delete location.');
        }
    } catch (error) {
        console.error('Error deleting location:', error);
        alert('通報の削除に失敗しました。');
    }
}

function addMarker(location) {
    const newMarker = L.marker([location.lat, location.lng]).addTo(map);

    const formattedDate = location.timestamp;

    let deleteButtonHtml = '';
    if (currentUser && location.user_id === currentUser) {
        deleteButtonHtml = `<button class="delete-button" data-location-id="${location.id}">この通報を削除</button>`;
    }

    newMarker.bindPopup(`
        クマが発見されました！
        <br>
        <br>
        <b>通報日時:</b> ${formattedDate}
        <br>
        ${deleteButtonHtml}
    `).openPopup();
    
    markers[location.id] = newMarker;
}

function initMap() {
    if (map) return;
    map = L.map('map').setView([35.681236, 139.767125], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    loadBearLocations();
}

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    checkLoginStatus();

    document.getElementById('sound-button').addEventListener('click', () => {
        const sound = document.getElementById('bear-sound');
        sound.play();
        alert('クマが嫌いな音を鳴らしました！');
    });

    document.getElementById('report-current-location-button').addEventListener('click', () => {
        const message = document.getElementById('report-message');
        message.textContent = '位置情報を取得しています...';
    
        if ("geolocation" in navigator) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    reportLocation(lat, lng);
                },
                (error) => {
                    console.error("Geolocation Error:", error);
                    alert("位置情報の取得に失敗しました。");
                    message.textContent = '位置情報の取得に失敗しました。';
                }
            );
        } else {
            alert("お使いのブラウザでは位置情報がサポートされていません。");
            message.textContent = '位置情報がサポートされていません。';
        }
    });

    document.getElementById('report-map-center-button').addEventListener('click', () => {
        const center = map.getCenter();
        reportLocation(center.lat, center.lng);
    });
    
    document.getElementById('logout-button').addEventListener('click', handleLogout);

    document.addEventListener('click', (event) => {
        if (event.target.classList.contains('delete-button')) {
            const locationId = event.target.dataset.locationId;
            if (locationId) {
                deleteBearLocation(locationId);
            }
        }
    });
});
