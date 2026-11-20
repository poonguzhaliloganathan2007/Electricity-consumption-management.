
package com.college.electricity;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.*;

@SpringBootApplication
@RestController
@RequestMapping("/api")
@CrossOrigin
public class ElectricityApplication {

    private final JdbcTemplate db;

    private static final BigDecimal RATE = new BigDecimal("5.00");
    private static final BigDecimal FIXED_CHARGE = new BigDecimal("30.00");

    public ElectricityApplication(JdbcTemplate db) {
        this.db = db;
    }

    public static void main(String[] args) {
        SpringApplication.run(ElectricityApplication.class, args);
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        return Map.of("status", "success",
                      "message", "Electricity Management System is running");
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody Map<String, String> data) {
        String username = data.get("username");
        String password = data.get("password");

        if ("admin".equals(username) && "admin123".equals(password)) {
            return ResponseEntity.ok(Map.of(
                    "status", "success",
                    "message", "Login successful",
                    "username", "admin"
            ));
        }

        return ResponseEntity.status(401).body(
                Map.of("status", "error", "message", "Invalid username or password")
        );
    }

    @GetMapping("/dashboard")
    public Map<String, Object> dashboard() {
        Integer consumers = db.queryForObject(
                "SELECT COUNT(*) FROM consumers", Integer.class);

        Integer readings = db.queryForObject(
                "SELECT COUNT(*) FROM readings", Integer.class);

        Double totalUnits = db.queryForObject(
                "SELECT COALESCE(SUM(units),0) FROM readings", Double.class);

        Double totalBills = db.queryForObject(
                "SELECT COALESCE(SUM(amount),0) FROM bills", Double.class);

        Integer pendingBills = db.queryForObject(
                "SELECT COUNT(*) FROM bills WHERE payment_status='Pending'",
                Integer.class);

        Map<String, Object> result = new HashMap<>();
        result.put("totalConsumers", consumers);
        result.put("totalReadings", readings);
        result.put("totalUnits", totalUnits);
        result.put("totalBills", totalBills);
        result.put("pendingBills", pendingBills);

        return result;
    }

    @PostMapping("/consumers")
    public ResponseEntity<?> addConsumer(@RequestBody Map<String, Object> data) {
        String number = String.valueOf(data.get("consumer_number"));
        String name = String.valueOf(data.get("full_name"));
        String address = String.valueOf(data.get("address"));
        String type = String.valueOf(data.get("connection_type"));

        db.update(
                "INSERT INTO consumers (consumer_number, full_name, address, connection_type) VALUES (?, ?, ?, ?)",
                number, name, address, type
        );

        return ResponseEntity.ok(Map.of(
                "status", "success",
                "message", "Consumer added successfully"
        ));
    }

    @GetMapping("/consumers")
    public List<Map<String, Object>> getConsumers() {
        return db.queryForList("SELECT * FROM consumers ORDER BY id DESC");
    }

    @PutMapping("/consumers/{id}")
    public ResponseEntity<?> updateConsumer(
            @PathVariable int id,
            @RequestBody Map<String, Object> data) {

        db.update(
                "UPDATE consumers SET consumer_number=?, full_name=?, address=?, connection_type=? WHERE id=?",
                data.get("consumer_number"),
                data.get("full_name"),
                data.get("address"),
                data.get("connection_type"),
                id
        );

        return ResponseEntity.ok(Map.of(
                "status", "success",
                "message", "Consumer updated successfully"
        ));
    }

    @DeleteMapping("/consumers/{id}")
    public ResponseEntity<?> deleteConsumer(@PathVariable int id) {
        db.update("DELETE FROM bills WHERE consumer_id=?", id);
        db.update("DELETE FROM readings WHERE consumer_id=?", id);
        db.update("DELETE FROM consumers WHERE id=?", id);

        return ResponseEntity.ok(Map.of(
                "status", "success",
                "message", "Consumer deleted successfully"
        ));
    }

    @PostMapping("/readings")
    public ResponseEntity<?> addReading(@RequestBody Map<String, Object> data) {

        int consumerId = Integer.parseInt(
                String.valueOf(data.get("consumer_id")));

        double previous = Double.parseDouble(
                String.valueOf(data.get("previous_reading")));

        double current = Double.parseDouble(
                String.valueOf(data.get("current_reading")));

        if (current < previous) {
            return ResponseEntity.badRequest().body(
                    Map.of("message", "Current reading cannot be less than previous reading")
            );
        }

        double units = current - previous;
        BigDecimal amount = RATE.multiply(BigDecimal.valueOf(units))
                .add(FIXED_CHARGE);

        String date = data.containsKey("reading_date")
                ? String.valueOf(data.get("reading_date"))
                : LocalDate.now().toString();

        db.update(
                "INSERT INTO readings (consumer_id, reading_date, previous_reading, current_reading, units) VALUES (?, ?, ?, ?, ?)",
                consumerId, date, previous, current, units
        );

        Integer readingId = db.queryForObject(
                "SELECT MAX(id) FROM readings WHERE consumer_id=?",
                Integer.class, consumerId
        );

        db.update(
                "INSERT INTO bills (consumer_id, reading_id, bill_month, units, amount, payment_status) VALUES (?, ?, ?, ?, ?, 'Pending')",
                consumerId,
                readingId,
                date.substring(0, 7),
                units,
                amount
        );

        return ResponseEntity.ok(Map.of(
                "status", "success",
                "units", units,
                "amount", amount,
                "message", "Reading saved and bill generated"
        ));
    }

    @GetMapping("/readings")
    public List<Map<String, Object>> getReadings() {
        return db.queryForList(
                "SELECT r.*, c.consumer_number, c.full_name FROM readings r JOIN consumers c ON r.consumer_id=c.id ORDER BY r.id DESC"
        );
    }

    @GetMapping("/bills")
    public List<Map<String, Object>> getBills() {
        return db.queryForList(
                "SELECT b.*, c.consumer_number, c.full_name FROM bills b JOIN consumers c ON b.consumer_id=c.id ORDER BY b.id DESC"
        );
    }

    @PutMapping("/bills/{id}/pay")
    public ResponseEntity<?> payBill(@PathVariable int id) {
        int updated = db.update(
                "UPDATE bills SET payment_status='Paid' WHERE id=?",
                id
        );

        if (updated == 0) {
            return ResponseEntity.notFound().build();
        }

        return ResponseEntity.ok(Map.of(
                "status", "success",
                "message", "Bill payment updated successfully"
        ));
    }

    @GetMapping("/analysis/monthly")
    public List<Map<String, Object>> monthlyAnalysis() {
        return db.queryForList(
                "SELECT bill_month, SUM(units) AS total_units, SUM(amount) AS total_amount FROM bills GROUP BY bill_month ORDER BY bill_month"
        );
    }

    @GetMapping("/reports/consumption.csv")
    public ResponseEntity<String> downloadReport() {

        List<Map<String, Object>> rows = db.queryForList(
                "SELECT c.consumer_number, c.full_name, r.reading_date, r.previous_reading, r.current_reading, r.units FROM readings r JOIN consumers c ON r.consumer_id=c.id ORDER BY r.reading_date"
        );

        StringBuilder csv = new StringBuilder();
        csv.append("Consumer Number,Name,Reading Date,Previous Reading,Current Reading,Units\n");

        for (Map<String, Object> row : rows) {
            csv.append(row.get("consumer_number")).append(",");
            csv.append("\"").append(row.get("full_name")).append("\",");
            csv.append(row.get("reading_date")).append(",");
            csv.append(row.get("previous_reading")).append(",");
            csv.append(row.get("current_reading")).append(",");
            csv.append(row.get("units")).append("\n");
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType("text/csv"));
        headers.set(
                HttpHeaders.CONTENT_DISPOSITION,
                "attachment; filename=electricity-report.csv"
        );

        return ResponseEntity.ok()
                .headers(headers)
                .body(csv.toString());
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<?> handleException(Exception ex) {
        ex.printStackTrace();

        return ResponseEntity.internalServerError().body(
                Map.of(
                        "status", "error",
                        "message", ex.getMessage() == null
                                ? "Something went wrong"
                                : ex.getMessage()
                )
        );
    }
}
