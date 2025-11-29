import { Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { useState, useEffect } from 'react';

interface TrendData {
    date: string;
    admissions: number;
    day_of_week: string;
}

interface TrendsChartProps {
    hospitalId?: string;
    days?: number;
}

export default function TrendsChart({ hospitalId = 'H001', days = 30 }: TrendsChartProps) {
    const [trendData, setTrendData] = useState<TrendData[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [average, setAverage] = useState(0);

    useEffect(() => {
        fetchTrends();
    }, [hospitalId, days]);

    const fetchTrends = async () => {
        try {
            setIsLoading(true);
            const response = await fetch(
                `http://localhost:8000/api/v1/predictions/trends/${hospitalId}?days=${days}`
            );
            const data = await response.json();
            if (data.status === 'success') {
                setTrendData(data.trends || []);
                setAverage(data.average || 0);
            }
        } catch (error) {
            console.error('Failed to fetch trends:', error);
        } finally {
            setIsLoading(false);
        }
    };

    // Format data for chart - show only every nth data point for better readability
    const chartData = trendData
        .filter((_, index) => days > 30 ? index % 3 === 0 : true)
        .map((item) => ({
            date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
            admissions: item.admissions,
            average: Math.round(average),
            dayOfWeek: item.day_of_week,
        }));

    // Custom tooltip
    const CustomTooltip = ({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
                <div style={{
                    background: 'white',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                    padding: '12px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                }}>
                    <p style={{ fontWeight: 600, marginBottom: '8px', color: '#111827' }}>
                        {data.date} ({data.dayOfWeek})
                    </p>
                    <p style={{ color: '#8B5CF6', fontSize: '14px', marginBottom: '4px' }}>
                        Admissions: <strong>{data.admissions}</strong>
                    </p>
                    <p style={{ color: '#6B7280', fontSize: '13px' }}>
                        Average: {data.average}
                    </p>
                    <p style={{
                        color: data.admissions > data.average ? '#EF4444' : '#10B981',
                        fontSize: '12px',
                        marginTop: '4px'
                    }}>
                        {data.admissions > data.average ? '▲' : '▼'} {Math.abs(data.admissions - data.average)} from avg
                    </p>
                </div>
            );
        }
        return null;
    };

    if (isLoading) {
        return (
            <div style={{
                width: '100%',
                height: '350px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#6B7280'
            }}>
                Loading trends...
            </div>
        );
    }

    return (
        <div style={{ width: '100%', height: '350px' }}>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                        <linearGradient id="colorTrend" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                    <XAxis
                        dataKey="date"
                        stroke="#6B7280"
                        style={{ fontSize: '12px' }}
                        interval="preserveStartEnd"
                    />
                    <YAxis
                        stroke="#6B7280"
                        style={{ fontSize: '12px' }}
                        label={{ value: 'Admissions', angle: -90, position: 'insideLeft', style: { fontSize: '12px', fill: '#6B7280' } }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                        wrapperStyle={{ fontSize: '14px', paddingTop: '20px' }}
                        iconType="line"
                    />
                    <Area
                        type="monotone"
                        dataKey="admissions"
                        stroke="#8B5CF6"
                        strokeWidth={2}
                        fill="url(#colorTrend)"
                        name="Daily Admissions"
                    />
                    <Line
                        type="monotone"
                        dataKey="average"
                        stroke="#F59E0B"
                        strokeWidth={2}
                        strokeDasharray="5 5"
                        dot={false}
                        name="Average"
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}