
const API = "/api";

const $ = selector => document.querySelector(selector);

async function api(url, options = {}) {
    const response = await fetch(API + url, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.message || data.error || "Something went wrong");
    }

    return data;
}

function toast(message) {
    const box = $("#toast");
    box.textContent = message;
    box.style.display = "block";
    setTimeout(() => box.style.display = "none", 3000);
}

function logout() {
    $("#mainApp").classList.add("hidden");
    $("#loginPage").classList.remove("hidden");
    $("#password").value = "";
}

function showPage(pageId) {
    document.querySelectorAll(".page").forEach(page => {
        page.classList.add("hidden");
    });

    $("#" + pageId).classList.remove("hidden");

    if (pageId === "dashboard") loadDashboard();
    if (pageId === "consumers") loadConsumers();

    if (pageId === "readings") {
        loadConsumers();
        loadReadings();
    }

    if (pageId === "bills") loadBills();
    if (pageId === "analysis") loadMonthly();
}

$("#loginForm").addEventListener("submit", async event => {
    event.preventDefault();

    try {
        await api("/login", {
            method: "POST",
            body: JSON.stringify({
                username: $("#username").value,
                password: $("#password").value
            })
        });

        $("#loginPage").classList.add("hidden");
        $("#mainApp").classList.remove("hidden");
        toast("Login successful!");
        showPage("dashboard");

    } catch (error) {
        $("#loginError").textContent = error.message;
    }
});

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

function createTable(headers, rows) {
    return `
        <div class="table-wrap">
            <table>
                <thead><tr>${headers.map(h => `<th>${h}</th>`).join("")}</tr></thead>
                <tbody>
                    ${rows.length
                        ? rows.map(row => `<tr>${row.map(v => `<td>${v ?? ""}</td>`).join("")}</tr>`).join("")
                        : `<tr><td colspan="${headers.length}">No records found</td></tr>`
                    }
                </tbody>
            </table>
        </div>`;
}

// DASHBOARD
async function loadDashboard() {
    try {
        const data = await api("/dashboard");

        $("#totalConsumers").textContent = data.totalConsumers ?? 0;
        $("#totalUnits").textContent = Number(data.totalUnits ?? 0).toFixed(2);
        $("#totalRevenue").textContent = "₹" + Number(data.totalBills ?? 0).toFixed(2);
        $("#unpaidBills").textContent = data.pendingBills ?? 0;

        loadMonthly();
    } catch (error) {
        toast(error.message);
    }
}

// CONSUMERS
async function loadConsumers() {
    try {
        const consumers = await api("/consumers");

        $("#consumerTable").innerHTML = createTable(
            ["ID", "Consumer Number", "Name", "Phone", "Address", "Connection", "Action"],
            consumers.map(c => [
                c.id,
                escapeHTML(c.consumer_number),
                escapeHTML(c.full_name),
                escapeHTML(c.phone),
                escapeHTML(c.address),
                escapeHTML(c.connection_type),
                `<button onclick="deleteConsumer(${c.id})">Delete</button>`
            ])
        );

        $("#consumerSelect").innerHTML =
            '<option value="">Select Consumer</option>' +
            consumers.map(c => `
                <option value="${c.id}">
                    ${escapeHTML(c.consumer_number)} - ${escapeHTML(c.full_name)}
                </option>
            `).join("");

    } catch (error) {
        toast(error.message);
    }
}

$("#consumerForm").addEventListener("submit", async event => {
    event.preventDefault();

    const form = new FormData(event.target);

    const data = {
        consumer_number: form.get("consumerNumber"),
        full_name: form.get("fullName"),
        phone: form.get("phone"),
        address: form.get("address"),
        connection_type: form.get("connectionType")
    };

    try {
        await api("/consumers", {
            method: "POST",
            body: JSON.stringify(data)
        });

        event.target.reset();
        toast("Consumer added successfully!");
        await loadConsumers();
        await loadDashboard();

    } catch (error) {
        toast(error.message);
    }
});

async function deleteConsumer(id) {
    if (!confirm("Delete this consumer?")) return;

    try {
        await api("/consumers/" + id, { method: "DELETE" });
        toast("Consumer deleted successfully!");
        await loadConsumers();
        await loadDashboard();
    } catch (error) {
        toast(error.message);
    }
}

// METER READINGS
$("#readingForm").addEventListener("submit", async event => {
    event.preventDefault();

    const form = new FormData(event.target);

    const data = {
        consumer_id: form.get("consumerId"),
        reading_date: form.get("readingDate"),
        previous_reading: form.get("previousReading"),
        current_reading: form.get("currentReading")
    };

    try {
        const result = await api("/readings", {
            method: "POST",
            body: JSON.stringify(data)
        });

        toast(`Reading saved! Units: ${result.units} | Bill: ₹${Number(result.amount).toFixed(2)}`);
        event.target.reset();

        await loadReadings();
        await loadBills();
        await loadDashboard();

    } catch (error) {
        toast(error.message);
    }
});

async function loadReadings() {
    try {
        const readings = await api("/readings");

        $("#readingTable").innerHTML = createTable(
            ["Date", "Consumer", "Previous", "Current", "Units"],
            readings.map(r => [
                r.reading_date,
                escapeHTML(r.consumer_number) + " - " + escapeHTML(r.full_name),
                r.previous_reading,
                r.current_reading,
                r.units
            ])
        );
    } catch (error) {
        toast(error.message);
    }
}

// BILLS
async function loadBills() {
    try {
        const bills = await api("/bills");

        $("#billTable").innerHTML = createTable(
            ["Month", "Consumer", "Units", "Amount", "Status", "Action"],
            bills.map(b => [
                b.bill_month,
                escapeHTML(b.consumer_number) + " - " + escapeHTML(b.full_name),
                b.units,
                "₹" + Number(b.amount).toFixed(2),
                escapeHTML(b.payment_status),
                b.payment_status === "Pending"
                    ? `<button onclick="payBill(${b.id})">Mark Paid</button>`
                    : "Completed"
            ])
        );
    } catch (error) {
        toast(error.message);
    }
}

async function payBill(id) {
    try {
        await api("/bills/" + id + "/pay", { method: "PUT" });
        toast("Payment updated!");
        await loadBills();
        await loadDashboard();
    } catch (error) {
        toast(error.message);
    }
}

// MONTHLY ANALYSIS
async function loadMonthly() {
    try {
        const records = await api("/analysis/monthly");

        const content = createTable(
            ["Month", "Total Units", "Total Amount"],
            records.map(r => [
                r.bill_month,
                Number(r.total_units).toFixed(2) + " units",
                "₹" + Number(r.total_amount).toFixed(2)
            ])
        );

        $("#monthlyDashboard").innerHTML = content;
        $("#monthlyAnalysis").innerHTML = content;

    } catch (error) {
        toast(error.message);
    }
}
