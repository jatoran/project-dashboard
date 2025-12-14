"use client";

import { useMemo } from "react";
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
} from "recharts";

interface MetricChartProps {
    data: Array<{
        timestamp: string;
        [key: string]: number | string | null | undefined;
    }>;
    dataKey: string;
    title: string;
    color?: string;
    unit?: string;
    maxY?: number;
    timeRange?: '1h' | '6h' | '24h' | '7d';
}

const COLORS = {
    indigo: { stroke: "#818cf8", fill: "#818cf8" },
    green: { stroke: "#34d399", fill: "#34d399" },
    amber: { stroke: "#fbbf24", fill: "#fbbf24" },
    red: { stroke: "#f87171", fill: "#f87171" },
    cyan: { stroke: "#22d3ee", fill: "#22d3ee" },
    purple: { stroke: "#a78bfa", fill: "#a78bfa" },
};

export default function MetricChart({
    data,
    dataKey,
    title,
    color = "indigo",
    unit = "",
    maxY,
    timeRange = "1h",
}: MetricChartProps) {
    const colorConfig = COLORS[color as keyof typeof COLORS] || COLORS.indigo;

    const chartData = useMemo(() => {
        return data.map((d) => {
            const date = new Date(d.timestamp);
            let label: string;

            if (timeRange === '7d') {
                // Show day + time for 7d
                label = date.toLocaleDateString([], { month: 'short', day: 'numeric' });
            } else if (timeRange === '24h') {
                // Show hour for 24h
                label = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            } else {
                // Show time for shorter ranges
                label = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }

            return { ...d, time: label };
        });
    }, [data, timeRange]);

    const latestValue = useMemo(() => {
        if (data.length === 0) return null;
        const last = data[data.length - 1];
        const val = last[dataKey];
        return typeof val === "number" ? val.toFixed(1) : null;
    }, [data, dataKey]);

    if (data.length === 0) {
        return (
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900">
                <div className="text-sm text-slate-400 mb-2">{title}</div>
                <div className="h-[120px] flex items-center justify-center text-slate-600 text-xs">
                    No data yet
                </div>
            </div>
        );
    }

    return (
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900">
            <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-400">{title}</span>
                {latestValue && (
                    <span className="text-lg font-semibold text-white">
                        {latestValue}
                        <span className="text-xs text-slate-500 ml-0.5">{unit}</span>
                    </span>
                )}
            </div>
            <div className="h-[120px]">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                        <defs>
                            <linearGradient id={`gradient-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={colorConfig.fill} stopOpacity={0.3} />
                                <stop offset="95%" stopColor={colorConfig.fill} stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <XAxis
                            dataKey="time"
                            tick={{ fontSize: 10, fill: "#64748b" }}
                            tickLine={false}
                            axisLine={false}
                            interval="preserveStartEnd"
                        />
                        <YAxis
                            tick={{ fontSize: 10, fill: "#64748b" }}
                            tickLine={false}
                            axisLine={false}
                            domain={[0, maxY || "auto"]}
                            tickFormatter={(v) => `${v}`}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: "#1e293b",
                                border: "1px solid #334155",
                                borderRadius: "8px",
                                fontSize: "12px",
                            }}
                            labelStyle={{ color: "#94a3b8" }}
                            formatter={(value: number) => [`${value?.toFixed(1)}${unit}`, title]}
                        />
                        <Area
                            type="monotone"
                            dataKey={dataKey}
                            stroke={colorConfig.stroke}
                            fill={`url(#gradient-${dataKey})`}
                            strokeWidth={2}
                            dot={false}
                            activeDot={{ r: 4, fill: colorConfig.stroke }}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
