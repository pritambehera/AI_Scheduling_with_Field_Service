package com.example.scheduling.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.ToString;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@ToString
public class ScheduleDto {
    private String id;
    private Double score;
    private List<AssignmentDto> assignments;

    @Data
    public static class AssignmentDto {
        private  String technicianId;
        private  String workOrderId;
        private String start;
        private String end;
        private TravelDto travel;
        private String rationale;
    }
    @Data
    public static class TravelDto {
        private double km;
        private int etaMin;
    }

}
