REPLACE INTO `ai_query_template_registry` (
  `template_id`,
  `tenant_id`,
  `template_name`,
  `template_category`,
  `template_sql`,
  `param_schema`,
  `result_schema`,
  `enabled_flag`
) VALUES
(
  'T01',
  'default',
  '当前节次',
  'realtime',
  'SELECT
  c.leti_number,
  c.leti_name,
  MIN(c.course_start_time) AS section_start_time,
  MAX(c.course_end_time) AS section_end_time
FROM t_tias_course c
WHERE c.delete_flag = 0
  AND c.tenant_id = %(tenant_id)s
  AND %(now_time)s BETWEEN c.course_start_time AND c.course_end_time
GROUP BY c.leti_number, c.leti_name
ORDER BY c.leti_number',
  '{"required":["now_time"],"properties":{"now_time":{"type":"datetime"}},"defaults":{}}',
  '{"leti_number":"integer","leti_name":"string","section_start_time":"datetime","section_end_time":"datetime"}',
  1
),
(
  'T02',
  'default',
  '当前在课课堂数',
  'realtime',
  'SELECT COUNT(DISTINCT c.classroom_id) AS active_classroom_count
FROM t_tias_course c
WHERE c.delete_flag = 0
  AND c.tenant_id = %(tenant_id)s
  AND %(now_time)s BETWEEN c.course_start_time AND c.course_end_time',
  '{"required":["now_time"],"properties":{"now_time":{"type":"datetime"}},"defaults":{}}',
  '{"active_classroom_count":"integer"}',
  1
),
(
  'T03',
  'default',
  '当前核心三率',
  'realtime',
  'SELECT
  ROUND(AVG(c.tias_att_percent), 2) AS avg_att_percent,
  ROUND(AVG(c.tias_front_full_percent), 2) AS avg_front_full_percent,
  ROUND(AVG(c.tias_rise_percent), 2) AS avg_rise_percent
FROM t_tias_course c
WHERE c.delete_flag = 0
  AND c.tenant_id = %(tenant_id)s
  AND %(now_time)s BETWEEN c.course_start_time AND c.course_end_time',
  '{"required":["now_time"],"properties":{"now_time":{"type":"datetime"}},"defaults":{}}',
  '{"avg_att_percent":"number","avg_front_full_percent":"number","avg_rise_percent":"number"}',
  1
),
(
  'T04',
  'default',
  '当前重点关注课堂数',
  'realtime',
  'SELECT COUNT(DISTINCT w.clro_id) AS focus_classroom_count
FROM (
  SELECT sr.clro_id
  FROM t_warning_study_record sr
  WHERE sr.delete_flag = 0
    AND sr.tenant_id = %(tenant_id)s
    AND sr.warning_time >= %(window_start)s
    AND sr.warning_level IN (1, 2)
  UNION ALL
  SELECT tr.clro_id
  FROM t_warning_teaching_record tr
  WHERE tr.delete_flag = 0
    AND tr.tenant_id = %(tenant_id)s
    AND tr.warning_time >= %(window_start)s
    AND tr.warning_level IN (1, 2)
  UNION ALL
  SELECT dr.clro_id
  FROM t_warning_device_record dr
  WHERE dr.delete_flag = 0
    AND dr.tenant_id = %(tenant_id)s
    AND dr.warning_time >= %(window_start)s
    AND dr.warning_level IN (1, 2)
  UNION ALL
  SELECT spr.clro_id
  FROM t_warning_space_record spr
  WHERE spr.delete_flag = 0
    AND spr.tenant_id = %(tenant_id)s
    AND spr.warning_time >= %(window_start)s
    AND spr.warning_level IN (1, 2)
) w
WHERE w.clro_id IS NOT NULL',
  '{"required":["window_start"],"properties":{"window_start":{"type":"datetime"},"now_time":{"type":"datetime"},"window_minutes":{"type":"integer"}},"defaults":{"window_minutes":30}}',
  '{"focus_classroom_count":"integer"}',
  1
),
(
  'T06',
  'default',
  '今日已结束课程核心均值',
  'daily',
  'SELECT
  COUNT(DISTINCT c.course_id) AS finished_course_count,
  ROUND(AVG(c.tias_att_percent), 2) AS today_avg_att_percent,
  ROUND(AVG(c.tias_front_full_percent), 2) AS today_avg_front_full_percent,
  ROUND(AVG(c.tias_rise_percent), 2) AS today_avg_rise_percent
FROM t_tias_course c
WHERE c.delete_flag = 0
  AND c.tenant_id = %(tenant_id)s
  AND DATE(c.course_end_time) = %(today)s
  AND c.course_end_time < %(now_time)s',
  '{"required":["today","now_time"],"properties":{"today":{"type":"date"},"now_time":{"type":"datetime"}},"defaults":{}}',
  '{"finished_course_count":"integer","today_avg_att_percent":"number","today_avg_front_full_percent":"number","today_avg_rise_percent":"number"}',
  1
),
(
  'T08',
  'default',
  '今日重点关注占比',
  'daily',
  'SELECT
  x.focus_classroom_count,
  x.total_classroom_count,
  ROUND(IFNULL(x.focus_classroom_count / NULLIF(x.total_classroom_count, 0), 0) * 100, 2) AS focus_ratio_percent
FROM (
  SELECT
    (
      SELECT COUNT(DISTINCT w.clro_id)
      FROM (
        SELECT sr.clro_id
        FROM t_warning_study_record sr
        WHERE sr.delete_flag = 0
          AND sr.tenant_id = %(tenant_id)s
          AND sr.warning_time_day = %(today)s
          AND sr.warning_level IN (1, 2)
        UNION ALL
        SELECT tr.clro_id
        FROM t_warning_teaching_record tr
        WHERE tr.delete_flag = 0
          AND tr.tenant_id = %(tenant_id)s
          AND tr.warning_time_day = %(today)s
          AND tr.warning_level IN (1, 2)
        UNION ALL
        SELECT dr.clro_id
        FROM t_warning_device_record dr
        WHERE dr.delete_flag = 0
          AND dr.tenant_id = %(tenant_id)s
          AND dr.warning_time_day = %(today)s
          AND dr.warning_level IN (1, 2)
        UNION ALL
        SELECT spr.clro_id
        FROM t_warning_space_record spr
        WHERE spr.delete_flag = 0
          AND spr.tenant_id = %(tenant_id)s
          AND spr.warning_time_day = %(today)s
          AND spr.warning_level IN (1, 2)
      ) w
      WHERE w.clro_id IS NOT NULL
    ) AS focus_classroom_count,
    (
      SELECT COUNT(DISTINCT c.classroom_id)
      FROM t_tias_course c
      WHERE c.delete_flag = 0
        AND c.tenant_id = %(tenant_id)s
        AND DATE(c.course_end_time) = %(today)s
    ) AS total_classroom_count
) x',
  '{"required":["today"],"properties":{"today":{"type":"date"}},"defaults":{}}',
  '{"focus_classroom_count":"integer","total_classroom_count":"integer","focus_ratio_percent":"number"}',
  1
),
(
  'T09',
  'default',
  '实时预警课堂占比',
  'realtime',
  'SELECT
  base.in_classroom_count,
  warn.warn_classroom_count,
  ROUND(IFNULL(warn.warn_classroom_count / NULLIF(base.in_classroom_count, 0), 0) * 100, 2) AS warn_ratio_percent
FROM
(
  SELECT COUNT(DISTINCT c.classroom_id) AS in_classroom_count
  FROM t_tias_course c
  WHERE c.delete_flag = 0
    AND c.tenant_id = %(tenant_id)s
    AND %(now_time)s BETWEEN c.course_start_time AND c.course_end_time
) base
CROSS JOIN
(
  SELECT COUNT(DISTINCT clro_id) AS warn_classroom_count
  FROM (
    SELECT sr.clro_id
    FROM t_warning_study_record sr
    WHERE sr.delete_flag = 0 AND sr.tenant_id = %(tenant_id)s
      AND sr.warning_time >= %(window_start)s
    UNION ALL
    SELECT tr.clro_id
    FROM t_warning_teaching_record tr
    WHERE tr.delete_flag = 0 AND tr.tenant_id = %(tenant_id)s
      AND tr.warning_time >= %(window_start)s
    UNION ALL
    SELECT dr.clro_id
    FROM t_warning_device_record dr
    WHERE dr.delete_flag = 0 AND dr.tenant_id = %(tenant_id)s
      AND dr.warning_time >= %(window_start)s
    UNION ALL
    SELECT spr.clro_id
    FROM t_warning_space_record spr
    WHERE spr.delete_flag = 0 AND spr.tenant_id = %(tenant_id)s
      AND spr.warning_time >= %(window_start)s
  ) t
  WHERE clro_id IS NOT NULL
) warn',
  '{"required":["now_time","window_start"],"properties":{"now_time":{"type":"datetime"},"window_start":{"type":"datetime"},"window_minutes":{"type":"integer"}},"defaults":{"window_minutes":30}}',
  '{"in_classroom_count":"integer","warn_classroom_count":"integer","warn_ratio_percent":"number"}',
  1
),
(
  'T10',
  'default',
  '实时整体风险等级',
  'realtime',
  'SELECT
  SUM(CASE WHEN x.warning_level = 1 THEN 1 ELSE 0 END) AS high_cnt,
  SUM(CASE WHEN x.warning_level = 2 THEN 1 ELSE 0 END) AS medium_cnt,
  SUM(CASE WHEN x.warning_level = 3 THEN 1 ELSE 0 END) AS low_cnt,
  SUM(CASE WHEN x.warning_level = 4 THEN 1 ELSE 0 END) AS tip_cnt,
  CASE
    WHEN SUM(CASE WHEN x.warning_level = 1 THEN 1 ELSE 0 END) >= 1 THEN ''高风险''
    WHEN SUM(CASE WHEN x.warning_level = 2 THEN 1 ELSE 0 END) >= 3 THEN ''中风险''
    WHEN COUNT(*) > 0 THEN ''低风险''
    ELSE ''无风险''
  END AS overall_risk_level
FROM (
  SELECT sr.warning_level
  FROM t_warning_study_record sr
  WHERE sr.delete_flag = 0 AND sr.tenant_id = %(tenant_id)s
    AND sr.warning_time >= %(window_start)s
  UNION ALL
  SELECT tr.warning_level
  FROM t_warning_teaching_record tr
  WHERE tr.delete_flag = 0 AND tr.tenant_id = %(tenant_id)s
    AND tr.warning_time >= %(window_start)s
  UNION ALL
  SELECT dr.warning_level
  FROM t_warning_device_record dr
  WHERE dr.delete_flag = 0 AND dr.tenant_id = %(tenant_id)s
    AND dr.warning_time >= %(window_start)s
  UNION ALL
  SELECT spr.warning_level
  FROM t_warning_space_record spr
  WHERE spr.delete_flag = 0 AND spr.tenant_id = %(tenant_id)s
    AND spr.warning_time >= %(window_start)s
) x',
  '{"required":["window_start"],"properties":{"window_start":{"type":"datetime"},"window_minutes":{"type":"integer"},"now_time":{"type":"datetime"}},"defaults":{"window_minutes":30}}',
  '{"high_cnt":"integer","medium_cnt":"integer","low_cnt":"integer","tip_cnt":"integer","overall_risk_level":"string"}',
  1
),
(
  'T11',
  'default',
  '实时预警类型分布',
  'realtime',
  'SELECT
  t.warn_domain,
  t.indicator_code,
  t.indicator_name,
  COUNT(*) AS warn_count
FROM (
  SELECT ''study'' AS warn_domain, sr.indicator_code, sr.indicator_name
  FROM t_warning_study_record sr
  WHERE sr.delete_flag = 0 AND sr.tenant_id = %(tenant_id)s
    AND sr.warning_time >= %(window_start)s
  UNION ALL
  SELECT ''teaching'' AS warn_domain, tr.indicator_code, tr.indicator_name
  FROM t_warning_teaching_record tr
  WHERE tr.delete_flag = 0 AND tr.tenant_id = %(tenant_id)s
    AND tr.warning_time >= %(window_start)s
  UNION ALL
  SELECT ''device'' AS warn_domain, dr.indicator_code, dr.indicator_name
  FROM t_warning_device_record dr
  WHERE dr.delete_flag = 0 AND dr.tenant_id = %(tenant_id)s
    AND dr.warning_time >= %(window_start)s
  UNION ALL
  SELECT ''space'' AS warn_domain, spr.indicator_code, spr.indicator_name
  FROM t_warning_space_record spr
  WHERE spr.delete_flag = 0 AND spr.tenant_id = %(tenant_id)s
    AND spr.warning_time >= %(window_start)s
) t
GROUP BY t.warn_domain, t.indicator_code, t.indicator_name
ORDER BY warn_count DESC',
  '{"required":["window_start"],"properties":{"window_start":{"type":"datetime"},"window_minutes":{"type":"integer"},"now_time":{"type":"datetime"}},"defaults":{"window_minutes":30}}',
  '{"warn_domain":"string","indicator_code":"string","indicator_name":"string","warn_count":"integer"}',
  1
),
(
  'T13',
  'default',
  '今日预警占比与风险',
  'daily',
  'SELECT
  a.warn_classroom_count,
  b.total_patrolled_classroom_count,
  ROUND(IFNULL(a.warn_classroom_count / NULLIF(b.total_patrolled_classroom_count, 0), 0) * 100, 2) AS warn_ratio_percent,
  CASE
    WHEN a.high_cnt >= 1 THEN ''高风险''
    WHEN a.medium_cnt >= 3 THEN ''中风险''
    WHEN a.warn_classroom_count > 0 THEN ''低风险''
    ELSE ''无风险''
  END AS overall_risk_level
FROM
(
  SELECT
    COUNT(DISTINCT t.clro_id) AS warn_classroom_count,
    SUM(CASE WHEN t.warning_level = 1 THEN 1 ELSE 0 END) AS high_cnt,
    SUM(CASE WHEN t.warning_level = 2 THEN 1 ELSE 0 END) AS medium_cnt
  FROM (
    SELECT sr.clro_id, sr.warning_level
    FROM t_warning_study_record sr
    WHERE sr.delete_flag = 0 AND sr.tenant_id = %(tenant_id)s
      AND sr.warning_time_day = %(today)s
    UNION ALL
    SELECT tr.clro_id, tr.warning_level
    FROM t_warning_teaching_record tr
    WHERE tr.delete_flag = 0 AND tr.tenant_id = %(tenant_id)s
      AND tr.warning_time_day = %(today)s
    UNION ALL
    SELECT dr.clro_id, dr.warning_level
    FROM t_warning_device_record dr
    WHERE dr.delete_flag = 0 AND dr.tenant_id = %(tenant_id)s
      AND dr.warning_time_day = %(today)s
    UNION ALL
    SELECT spr.clro_id, spr.warning_level
    FROM t_warning_space_record spr
    WHERE spr.delete_flag = 0 AND spr.tenant_id = %(tenant_id)s
      AND spr.warning_time_day = %(today)s
  ) t
  WHERE t.clro_id IS NOT NULL
) a
CROSS JOIN
(
  SELECT COUNT(DISTINCT c.classroom_id) AS total_patrolled_classroom_count
  FROM t_tias_course c
  WHERE c.delete_flag = 0
    AND c.tenant_id = %(tenant_id)s
    AND DATE(c.course_end_time) = %(today)s
) b',
  '{"required":["today"],"properties":{"today":{"type":"date"}},"defaults":{}}',
  '{"warn_classroom_count":"integer","total_patrolled_classroom_count":"integer","warn_ratio_percent":"number","overall_risk_level":"string"}',
  1
);

REPLACE INTO `ai_metric_definition` (
  `metric_code`,
  `metric_name`,
  `metric_definition`,
  `stat_rule`,
  `source_tables`,
  `source_fields`,
  `template_id`,
  `default_time_range`,
  `tenant_id`
) VALUES
(
  'current_section',
  '当前节次',
  '当前时间命中的课程节次信息',
  '当前时间落在课程开始时间和结束时间之间',
  't_tias_course',
  'leti_number, leti_name, course_start_time, course_end_time',
  'T01',
  'now',
  'default'
),
(
  'current_active_classroom_count',
  '当前在课课堂数',
  '当前正在上课的教室数量',
  '当前时间窗口内按 classroom_id 去重',
  't_tias_course',
  'classroom_id, course_start_time, course_end_time',
  'T02',
  'now',
  'default'
),
(
  'current_core_rates',
  '当前核心三率',
  '当前在课课程的平均到课率、前排满座率、抬头率',
  '当前在课课程求平均',
  't_tias_course',
  'tias_att_percent, tias_front_full_percent, tias_rise_percent',
  'T03',
  'now',
  'default'
),
(
  'current_focus_classroom_count',
  '当前重点关注课堂数',
  '最近时间窗内高/中等级预警涉及的课堂数',
  '按 clro_id 去重，预警等级固定为 1/2',
  't_warning_study_record,t_warning_teaching_record,t_warning_device_record,t_warning_space_record',
  'clro_id, warning_level, warning_time',
  'T04',
  'last_30_minutes',
  'default'
),
(
  'today_avg_attendance',
  '今日课堂平均到课率',
  '今日已结束课程的平均到课率',
  '按今日已结束课程求平均',
  't_tias_course',
  'course_end_time, tias_att_percent',
  'T06',
  'today',
  'default'
),
(
  'today_focus_ratio',
  '今日重点关注课堂占比',
  '今日重点关注课堂数占今日已结束课堂数比例',
  '分子为今日高/中等级预警课堂数，分母为今日课堂数',
  't_tias_course,t_warning_*_record',
  'classroom_id, clro_id, warning_time_day',
  'T08',
  'today',
  'default'
),
(
  'realtime_warn_ratio',
  '实时预警课堂占比',
  '当前在课课堂中，出现预警的课堂占比',
  '分子为最近时间窗内预警课堂数，分母为当前在课课堂数',
  't_tias_course,t_warning_*_record',
  'classroom_id, clro_id, warning_time',
  'T09',
  'last_30_minutes',
  'default'
),
(
  'realtime_overall_risk_level',
  '实时整体风险等级',
  '根据最近时间窗内预警等级汇总得到整体风险等级',
  '高风险优先，其次中风险，再到低风险',
  't_warning_study_record,t_warning_teaching_record,t_warning_device_record,t_warning_space_record',
  'warning_level, warning_time',
  'T10',
  'last_30_minutes',
  'default'
),
(
  'realtime_warn_distribution',
  '实时预警类型分布',
  '按预警域和指标统计最近时间窗内预警数量',
  '按 warn_domain, indicator_code, indicator_name 聚合',
  't_warning_study_record,t_warning_teaching_record,t_warning_device_record,t_warning_space_record',
  'indicator_code, indicator_name, warning_time',
  'T11',
  'last_30_minutes',
  'default'
),
(
  'today_warn_ratio_and_risk',
  '今日预警占比与风险',
  '今日预警课堂占比与整体风险等级',
  '今日预警课堂数除以今日已完成AI巡查课堂数，并按等级判断风险',
  't_tias_course,t_warning_*_record',
  'classroom_id, clro_id, warning_time_day, warning_level',
  'T13',
  'today',
  'default'
);
