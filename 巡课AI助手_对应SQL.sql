/*
  巡课AI助手 - 对应SQL整理（MySQL 5.7）
  说明：
  1) 所有查询默认只统计 delete_flag=0 数据。
  2) 通过 @tenant_id 约束租户；按需替换。
  3) “活力值”先按规则公式演示，可后续替换为模型打分。
*/

SET @tenant_id = 'YOUR_TENANT_ID';
SET @now_time = NOW();
SET @today = CURDATE();

/* ============================================================
   A. 需求1：课表时间段智能巡课（实时简报）
   ============================================================ */

/* A1 当前节次 */
SELECT
  c.leti_number,
  c.leti_name,
  MIN(c.course_start_time) AS section_start_time,
  MAX(c.course_end_time) AS section_end_time
FROM t_tias_course c
WHERE c.delete_flag = 0
  AND c.tenant_id = @tenant_id
  AND @now_time BETWEEN c.course_start_time AND c.course_end_time
GROUP BY c.leti_number, c.leti_name
ORDER BY c.leti_number;

/* A2 正在上课课堂数量（按 classroom_id 去重） */
SELECT COUNT(DISTINCT c.classroom_id) AS active_classroom_count
FROM t_tias_course c
WHERE c.delete_flag = 0
  AND c.tenant_id = @tenant_id
  AND @now_time BETWEEN c.course_start_time AND c.course_end_time;

/* A3 AI巡查轮次（近似：按5分钟时间桶） */
SELECT COUNT(DISTINCT x.round_bucket) AS ai_round_count_approx
FROM (
  SELECT FROM_UNIXTIME(UNIX_TIMESTAMP(d.tias_event_time) - MOD(UNIX_TIMESTAMP(d.tias_event_time), 300)) AS round_bucket
  FROM t_tias_course_student_detail d
  WHERE d.delete_flag = 0
    AND d.tenant_id = @tenant_id
    AND d.tias_event_time >= DATE_SUB(@now_time, INTERVAL 2 HOUR)

  UNION

  SELECT FROM_UNIXTIME(UNIX_TIMESTAMP(d.tias_event_time) - MOD(UNIX_TIMESTAMP(d.tias_event_time), 300)) AS round_bucket
  FROM t_tias_course_teacher_detail d
  WHERE d.delete_flag = 0
    AND d.tenant_id = @tenant_id
    AND d.tias_event_time >= DATE_SUB(@now_time, INTERVAL 2 HOUR)
) x;

/* A4 当前课堂平均到课率 / 前排满座率 / 抬头率 */
SELECT
  ROUND(AVG(c.tias_att_percent), 2) AS avg_att_percent,
  ROUND(AVG(c.tias_front_full_percent), 2) AS avg_front_full_percent,
  ROUND(AVG(c.tias_rise_percent), 2) AS avg_rise_percent
FROM t_tias_course c
WHERE c.delete_flag = 0
  AND c.tenant_id = @tenant_id
  AND @now_time BETWEEN c.course_start_time AND c.course_end_time;

/* A5 重点关注课堂数量（预警等级高/中，按教室去重） */
SELECT COUNT(DISTINCT w.clro_id) AS focus_classroom_count
FROM (
  SELECT sr.clro_id
  FROM t_warning_study_record sr
  WHERE sr.delete_flag = 0
    AND sr.tenant_id = @tenant_id
    AND sr.warning_time >= DATE_SUB(@now_time, INTERVAL 30 MINUTE)
    AND sr.warning_level IN (1, 2)

  UNION ALL

  SELECT tr.clro_id
  FROM t_warning_teaching_record tr
  WHERE tr.delete_flag = 0
    AND tr.tenant_id = @tenant_id
    AND tr.warning_time >= DATE_SUB(@now_time, INTERVAL 30 MINUTE)
    AND tr.warning_level IN (1, 2)

  UNION ALL

  SELECT dr.clro_id
  FROM t_warning_device_record dr
  WHERE dr.delete_flag = 0
    AND dr.tenant_id = @tenant_id
    AND dr.warning_time >= DATE_SUB(@now_time, INTERVAL 30 MINUTE)
    AND dr.warning_level IN (1, 2)

  UNION ALL

  SELECT spr.clro_id
  FROM t_warning_space_record spr
  WHERE spr.delete_flag = 0
    AND spr.tenant_id = @tenant_id
    AND spr.warning_time >= DATE_SUB(@now_time, INTERVAL 30 MINUTE)
    AND spr.warning_level IN (1, 2)
) w
WHERE w.clro_id IS NOT NULL;

/* A6 活力值较高课堂数量（规则版，阈值70） */
SELECT COUNT(*) AS high_vitality_classroom_count
FROM (
  SELECT
    c.course_id,
    c.classroom_id,
    ROUND(
      0.35 * IFNULL(c.tias_rise_percent, 0)
      + 0.35 * IFNULL(c.tias_avg_concentration, 0)
      + 0.15 * (100 - LEAST(IFNULL(c.tias_avg_phone_use_num, 0) * 5, 100))
      + 0.15 * (100 - LEAST(IFNULL(c.tias_avg_sleep_num, 0) * 5, 100)),
      2
    ) AS vitality_score
  FROM t_tias_course c
  WHERE c.delete_flag = 0
    AND c.tenant_id = @tenant_id
    AND @now_time BETWEEN c.course_start_time AND c.course_end_time
) t
WHERE t.vitality_score >= 70;


/* ============================================================
   B. 需求2：非课表时间段智能巡课（今日简报）
   ============================================================ */

/* B1 今日已结束课程的核心均值 */
SELECT
  COUNT(DISTINCT c.course_id) AS finished_course_count,
  ROUND(AVG(c.tias_att_percent), 2) AS today_avg_att_percent,
  ROUND(AVG(c.tias_front_full_percent), 2) AS today_avg_front_full_percent,
  ROUND(AVG(c.tias_rise_percent), 2) AS today_avg_rise_percent
FROM t_tias_course c
WHERE c.delete_flag = 0
  AND c.tenant_id = @tenant_id
  AND DATE(c.course_end_time) = @today
  AND c.course_end_time < @now_time;

/* B2 今日课堂活动数据（课程汇总口径） */
SELECT
  ROUND(AVG(c.tias_avg_reading_num), 2) AS today_avg_reading_num,
  ROUND(AVG(c.tias_avg_phone_use_num), 2) AS today_avg_phone_use_num,
  ROUND(AVG(c.tias_avg_sleep_num), 2) AS today_avg_sleep_num,
  ROUND(AVG(c.tias_avg_concentration), 2) AS today_avg_concentration
FROM t_tias_course c
WHERE c.delete_flag = 0
  AND c.tenant_id = @tenant_id
  AND DATE(c.course_end_time) = @today
  AND c.course_end_time < @now_time;

/* B3 今日重点关注课堂数量 + 占比 */
SELECT
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
          AND sr.tenant_id = @tenant_id
          AND sr.warning_time_day = @today
          AND sr.warning_level IN (1, 2)
        UNION ALL
        SELECT tr.clro_id
        FROM t_warning_teaching_record tr
        WHERE tr.delete_flag = 0
          AND tr.tenant_id = @tenant_id
          AND tr.warning_time_day = @today
          AND tr.warning_level IN (1, 2)
        UNION ALL
        SELECT dr.clro_id
        FROM t_warning_device_record dr
        WHERE dr.delete_flag = 0
          AND dr.tenant_id = @tenant_id
          AND dr.warning_time_day = @today
          AND dr.warning_level IN (1, 2)
        UNION ALL
        SELECT spr.clro_id
        FROM t_warning_space_record spr
        WHERE spr.delete_flag = 0
          AND spr.tenant_id = @tenant_id
          AND spr.warning_time_day = @today
          AND spr.warning_level IN (1, 2)
      ) w
      WHERE w.clro_id IS NOT NULL
    ) AS focus_classroom_count,
    (
      SELECT COUNT(DISTINCT c.classroom_id)
      FROM t_tias_course c
      WHERE c.delete_flag = 0
        AND c.tenant_id = @tenant_id
        AND DATE(c.course_end_time) = @today
    ) AS total_classroom_count
) x;


/* ============================================================
   C. 需求3/4：实时AI预警 + 今日AI预警
   ============================================================ */

/* C1 当前在课课堂数 / 预警课堂数 / 预警占比 */
SELECT
  base.in_classroom_count,
  warn.warn_classroom_count,
  ROUND(IFNULL(warn.warn_classroom_count / NULLIF(base.in_classroom_count, 0), 0) * 100, 2) AS warn_ratio_percent
FROM
(
  SELECT COUNT(DISTINCT c.classroom_id) AS in_classroom_count
  FROM t_tias_course c
  WHERE c.delete_flag = 0
    AND c.tenant_id = @tenant_id
    AND @now_time BETWEEN c.course_start_time AND c.course_end_time
) base
CROSS JOIN
(
  SELECT COUNT(DISTINCT clro_id) AS warn_classroom_count
  FROM (
    SELECT sr.clro_id
    FROM t_warning_study_record sr
    WHERE sr.delete_flag = 0 AND sr.tenant_id = @tenant_id
      AND sr.warning_time >= DATE_SUB(@now_time, INTERVAL 30 MINUTE)
    UNION ALL
    SELECT tr.clro_id
    FROM t_warning_teaching_record tr
    WHERE tr.delete_flag = 0 AND tr.tenant_id = @tenant_id
      AND tr.warning_time >= DATE_SUB(@now_time, INTERVAL 30 MINUTE)
    UNION ALL
    SELECT dr.clro_id
    FROM t_warning_device_record dr
    WHERE dr.delete_flag = 0 AND dr.tenant_id = @tenant_id
      AND dr.warning_time >= DATE_SUB(@now_time, INTERVAL 30 MINUTE)
    UNION ALL
    SELECT spr.clro_id
    FROM t_warning_space_record spr
    WHERE spr.delete_flag = 0 AND spr.tenant_id = @tenant_id
      AND spr.warning_time >= DATE_SUB(@now_time, INTERVAL 30 MINUTE)
  ) t
  WHERE clro_id IS NOT NULL
) warn;

/* C2 实时整体预警风险等级（高=1/中=2/低=3/提示=4） */
SELECT
  SUM(CASE WHEN x.warning_level = 1 THEN 1 ELSE 0 END) AS high_cnt,
  SUM(CASE WHEN x.warning_level = 2 THEN 1 ELSE 0 END) AS medium_cnt,
  SUM(CASE WHEN x.warning_level = 3 THEN 1 ELSE 0 END) AS low_cnt,
  SUM(CASE WHEN x.warning_level = 4 THEN 1 ELSE 0 END) AS tip_cnt,
  CASE
    WHEN SUM(CASE WHEN x.warning_level = 1 THEN 1 ELSE 0 END) >= 1 THEN '高风险'
    WHEN SUM(CASE WHEN x.warning_level = 2 THEN 1 ELSE 0 END) >= 3 THEN '中风险'
    WHEN COUNT(*) > 0 THEN '低风险'
    ELSE '无风险'
  END AS overall_risk_level
FROM (
  SELECT sr.warning_level
  FROM t_warning_study_record sr
  WHERE sr.delete_flag = 0 AND sr.tenant_id = @tenant_id
    AND sr.warning_time >= DATE_SUB(@now_time, INTERVAL 30 MINUTE)

  UNION ALL

  SELECT tr.warning_level
  FROM t_warning_teaching_record tr
  WHERE tr.delete_flag = 0 AND tr.tenant_id = @tenant_id
    AND tr.warning_time >= DATE_SUB(@now_time, INTERVAL 30 MINUTE)

  UNION ALL

  SELECT dr.warning_level
  FROM t_warning_device_record dr
  WHERE dr.delete_flag = 0 AND dr.tenant_id = @tenant_id
    AND dr.warning_time >= DATE_SUB(@now_time, INTERVAL 30 MINUTE)

  UNION ALL

  SELECT spr.warning_level
  FROM t_warning_space_record spr
  WHERE spr.delete_flag = 0 AND spr.tenant_id = @tenant_id
    AND spr.warning_time >= DATE_SUB(@now_time, INTERVAL 30 MINUTE)
) x;

/* C3 预警类型分布（实时） */
SELECT
  t.warn_domain,
  t.indicator_code,
  t.indicator_name,
  COUNT(*) AS warn_count
FROM (
  SELECT 'study' AS warn_domain, sr.indicator_code, sr.indicator_name
  FROM t_warning_study_record sr
  WHERE sr.delete_flag = 0 AND sr.tenant_id = @tenant_id
    AND sr.warning_time >= DATE_SUB(@now_time, INTERVAL 30 MINUTE)

  UNION ALL

  SELECT 'teaching' AS warn_domain, tr.indicator_code, tr.indicator_name
  FROM t_warning_teaching_record tr
  WHERE tr.delete_flag = 0 AND tr.tenant_id = @tenant_id
    AND tr.warning_time >= DATE_SUB(@now_time, INTERVAL 30 MINUTE)

  UNION ALL

  SELECT 'device' AS warn_domain, dr.indicator_code, dr.indicator_name
  FROM t_warning_device_record dr
  WHERE dr.delete_flag = 0 AND dr.tenant_id = @tenant_id
    AND dr.warning_time >= DATE_SUB(@now_time, INTERVAL 30 MINUTE)

  UNION ALL

  SELECT 'space' AS warn_domain, spr.indicator_code, spr.indicator_name
  FROM t_warning_space_record spr
  WHERE spr.delete_flag = 0 AND spr.tenant_id = @tenant_id
    AND spr.warning_time >= DATE_SUB(@now_time, INTERVAL 30 MINUTE)
) t
GROUP BY t.warn_domain, t.indicator_code, t.indicator_name
ORDER BY warn_count DESC;

/* C4 今日已巡查课堂数量（有学情或教情明细事件） */
SELECT COUNT(DISTINCT x.course_id) AS today_patrolled_course_count
FROM (
  SELECT d.course_id
  FROM t_tias_course_student_detail d
  WHERE d.delete_flag = 0
    AND d.tenant_id = @tenant_id
    AND DATE(d.tias_event_time) = @today

  UNION

  SELECT d.course_id
  FROM t_tias_course_teacher_detail d
  WHERE d.delete_flag = 0
    AND d.tenant_id = @tenant_id
    AND DATE(d.tias_event_time) = @today
) x
WHERE x.course_id IS NOT NULL;

/* C5 今日预警课堂数量/占比/整体风险 */
SELECT
  a.warn_classroom_count,
  b.total_patrolled_classroom_count,
  ROUND(IFNULL(a.warn_classroom_count / NULLIF(b.total_patrolled_classroom_count, 0), 0) * 100, 2) AS warn_ratio_percent,
  CASE
    WHEN a.high_cnt >= 1 THEN '高风险'
    WHEN a.medium_cnt >= 3 THEN '中风险'
    WHEN a.warn_classroom_count > 0 THEN '低风险'
    ELSE '无风险'
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
    WHERE sr.delete_flag = 0 AND sr.tenant_id = @tenant_id
      AND sr.warning_time_day = @today
    UNION ALL
    SELECT tr.clro_id, tr.warning_level
    FROM t_warning_teaching_record tr
    WHERE tr.delete_flag = 0 AND tr.tenant_id = @tenant_id
      AND tr.warning_time_day = @today
    UNION ALL
    SELECT dr.clro_id, dr.warning_level
    FROM t_warning_device_record dr
    WHERE dr.delete_flag = 0 AND dr.tenant_id = @tenant_id
      AND dr.warning_time_day = @today
    UNION ALL
    SELECT spr.clro_id, spr.warning_level
    FROM t_warning_space_record spr
    WHERE spr.delete_flag = 0 AND spr.tenant_id = @tenant_id
      AND spr.warning_time_day = @today
  ) t
  WHERE t.clro_id IS NOT NULL
) a
CROSS JOIN
(
  SELECT COUNT(DISTINCT c.classroom_id) AS total_patrolled_classroom_count
  FROM t_tias_course c
  WHERE c.delete_flag = 0
    AND c.tenant_id = @tenant_id
    AND DATE(c.course_end_time) = @today
) b;


/* ============================================================
   D. 需求5：预警消息智能推送相关
   ============================================================ */

/* D1 获取课程授课教师接收清单 */
SELECT
  ct.course_id,
  ct.teacher_user_id AS receiver_user_id,
  ct.teacher_user_code AS receiver_user_code,
  ct.teacher_user_name AS receiver_user_name
FROM t_warning_course_teacher ct
WHERE ct.delete_flag = 0
  AND ct.tenant_id = @tenant_id
  AND ct.course_id = ?;

/* D2 写入待发送接收人（示例） */
INSERT INTO t_warning_feedback_receiver_user (
  id, record_id, warning_message_type, read_status,
  receiver_user_id, receiver_user_code, receiver_user_name,
  batch_no, batch_time,
  create_user_id, update_user_id, version,
  created_date_time, created_by, last_modified_date_time, last_modified_by,
  delete_flag, tenant_id
)
VALUES (
  ?, ?, ?, 0,
  ?, ?, ?,
  ?, NOW(),
  ?, ?, 1,
  NOW(), ?, NOW(), ?,
  0, @tenant_id
);

/* D3 阈值策略查询（已启用） */
SELECT
  s.id AS strategy_id,
  s.alarm_strategy_name,
  s.alarm_enable,
  e.id AS event_id,
  e.indicator_id,
  e.alarm_frequency,
  e.alarm_range_type,
  e.class_from,
  e.class_to,
  e.course_time_status,
  e.rules_json
FROM t_patrol_alarm_strategy s
JOIN t_patrol_alarm_strategy_event_relation r
  ON r.alarm_strategy_id = s.id
 AND r.delete_flag = 0
 AND r.tenant_id = s.tenant_id
JOIN t_patrol_alarm_event e
  ON e.id = r.alarm_event_id
 AND e.delete_flag = 0
 AND e.tenant_id = s.tenant_id
WHERE s.delete_flag = 0
  AND s.tenant_id = @tenant_id
  AND s.alarm_enable = 1;


/* ============================================================
   E. 需求6：视频打点（现状查询 + 建议新增结果表）
   ============================================================ */

/* E1 课程视频与音频任务基础关联 */
SELECT
  t.cour_id AS course_id,
  t.task_id,
  t.stream_type,
  t.status,
  vr.file_url,
  vr.vod_start_time,
  vr.vod_end_time
FROM t_voice_analysis_task t
LEFT JOIN t_media_video_record vr
  ON vr.delete_flag = 0
 AND vr.tenant_id = t.tenant_id
 AND vr.vod_start_time <= t.course_end_time
 AND vr.vod_end_time >= t.course_start_time
WHERE t.delete_flag = 0
  AND t.tenant_id = @tenant_id
  AND t.cour_id = ?;

/* E2 现有音频时间段数据 */
SELECT
  h.task_id,
  h.start_time_second,
  h.end_time_second,
  h.volume_db,
  h.start_time,
  h.end_time
FROM t_voice_analysis_history h
WHERE h.delete_flag = 0
  AND h.tenant_id = @tenant_id
  AND h.task_id = ?
ORDER BY h.start_time_second;


/* ============================================================
   F. 缺失能力对应DDL（按文档建议）
   ============================================================ */

/* F1 巡查轮次任务表 */
DROP TABLE IF EXISTS `t_patrol_round_task`;
CREATE TABLE `t_patrol_round_task` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `round_id` varchar(64) NOT NULL COMMENT '巡查轮次ID（业务唯一）',
  `course_id` bigint(20) DEFAULT NULL COMMENT '课程id',
  `round_total` int(11) DEFAULT NULL COMMENT '计划总轮次',
  `current_round` int(11) DEFAULT NULL COMMENT '当前轮次',
  `progress` decimal(5,2) DEFAULT NULL COMMENT '进度百分比',
  `snapshot_time` datetime DEFAULT NULL COMMENT '快照时间',
  `status` tinyint(4) DEFAULT '0' COMMENT '状态 0未开始 1进行中 2已完成 3失败',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_round_id_tenant` (`round_id`,`tenant_id`) USING BTREE,
  KEY `idx_course_snapshot` (`course_id`,`snapshot_time`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='巡课轮次任务进度表';

/* F2 辅导员-课程/教学班映射 */
DROP TABLE IF EXISTS `t_counselor_course_rel`;
CREATE TABLE `t_counselor_course_rel` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `counselor_id` bigint(20) NOT NULL COMMENT '辅导员用户id',
  `counselor_code` varchar(64) DEFAULT NULL COMMENT '辅导员工号',
  `counselor_name` varchar(255) DEFAULT NULL COMMENT '辅导员姓名',
  `teaching_class_id` bigint(20) DEFAULT NULL COMMENT '教学班id',
  `course_id` bigint(20) DEFAULT NULL COMMENT '课程id（可空）',
  `org_id` bigint(20) DEFAULT NULL COMMENT '组织id',
  `effective_start_time` datetime DEFAULT NULL COMMENT '生效开始时间',
  `effective_end_time` datetime DEFAULT NULL COMMENT '生效结束时间',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_counselor_id` (`counselor_id`) USING BTREE,
  KEY `idx_teaching_class_id` (`teaching_class_id`) USING BTREE,
  KEY `idx_course_id` (`course_id`) USING BTREE,
  KEY `idx_org_id` (`org_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='辅导员与课程/教学班关系表';

/* F3 消息通道配置 */
DROP TABLE IF EXISTS `t_message_channel_config`;
CREATE TABLE `t_message_channel_config` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `channel_code` varchar(64) NOT NULL COMMENT '通道编码：wecom/wechat/campus_im',
  `channel_name` varchar(255) DEFAULT NULL COMMENT '通道名称',
  `enable_flag` tinyint(4) DEFAULT '1' COMMENT '启用标识 0否 1是',
  `config_json` json DEFAULT NULL COMMENT '通道参数配置',
  `retry_times` int(11) DEFAULT '3' COMMENT '失败重试次数',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_channel_code_tenant` (`channel_code`,`tenant_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='消息通道配置表';

/* F4 预警消息投递日志 */
DROP TABLE IF EXISTS `t_warning_message_delivery_log`;
CREATE TABLE `t_warning_message_delivery_log` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `record_id` bigint(20) NOT NULL COMMENT '预警记录ID',
  `warning_message_type` varchar(32) NOT NULL COMMENT 'study/teaching/device/space',
  `batch_no` bigint(20) DEFAULT NULL COMMENT '批次号',
  `channel_code` varchar(64) NOT NULL COMMENT '消息通道编码',
  `receiver_user_id` bigint(20) DEFAULT NULL COMMENT '接收人id',
  `receiver_user_code` varchar(255) DEFAULT NULL COMMENT '接收人工号',
  `receiver_user_name` varchar(255) DEFAULT NULL COMMENT '接收人姓名',
  `send_status` tinyint(4) DEFAULT '0' COMMENT '发送状态 0待发送 1成功 2失败',
  `send_time` datetime DEFAULT NULL COMMENT '发送时间',
  `error_msg` varchar(2000) DEFAULT NULL COMMENT '失败原因',
  `receipt_status` tinyint(4) DEFAULT NULL COMMENT '回执状态 0未回执 1已送达 2已读',
  `receipt_time` datetime DEFAULT NULL COMMENT '回执时间',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_record_msg_type` (`record_id`,`warning_message_type`) USING BTREE,
  KEY `idx_receiver_batch` (`receiver_user_id`,`batch_no`) USING BTREE,
  KEY `idx_channel_send_time` (`channel_code`,`send_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='预警消息投递日志表';

/* F5 课程活力值 */
DROP TABLE IF EXISTS `t_course_vitality_score`;
CREATE TABLE `t_course_vitality_score` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `course_id` bigint(20) NOT NULL COMMENT '课程id',
  `classroom_id` bigint(20) DEFAULT NULL COMMENT '教室id',
  `calc_time` datetime DEFAULT NULL COMMENT '计算时间',
  `vitality_score` decimal(6,2) DEFAULT NULL COMMENT '活力值分数',
  `vitality_level` varchar(20) DEFAULT NULL COMMENT '活力等级 high/medium/low',
  `rule_version` varchar(64) DEFAULT NULL COMMENT '规则版本',
  `model_version` varchar(64) DEFAULT NULL COMMENT '模型版本',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_course_calc_time` (`course_id`,`calc_time`) USING BTREE,
  KEY `idx_vitality_level` (`vitality_level`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='课程活力值评分表';

/* F6 视频ASR片段 */
DROP TABLE IF EXISTS `t_video_asr_segment`;
CREATE TABLE `t_video_asr_segment` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `task_id` varchar(64) NOT NULL COMMENT '音频分析任务ID',
  `course_id` bigint(20) DEFAULT NULL COMMENT '课程id',
  `start_sec` decimal(10,3) NOT NULL COMMENT '片段开始秒',
  `end_sec` decimal(10,3) NOT NULL COMMENT '片段结束秒',
  `transcript` text COMMENT 'ASR文本',
  `keywords` text COMMENT '关键词（json数组或逗号分隔）',
  `summary` text COMMENT '片段摘要',
  `confidence` decimal(5,2) DEFAULT NULL COMMENT '置信度',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_task_time` (`task_id`,`start_sec`,`end_sec`) USING BTREE,
  KEY `idx_course_id` (`course_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='视频ASR分段结果表';

/* F7 PPT页帧结果 */
DROP TABLE IF EXISTS `t_ppt_frame`;
CREATE TABLE `t_ppt_frame` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `task_id` varchar(64) NOT NULL COMMENT '分析任务ID',
  `course_id` bigint(20) DEFAULT NULL COMMENT '课程id',
  `page_no` int(11) NOT NULL COMMENT '页码',
  `thumbnail_url` varchar(512) DEFAULT NULL COMMENT '缩略图地址',
  `ocr_text` text COMMENT 'OCR文本',
  `page_summary` text COMMENT '页级摘要',
  `capture_sec` decimal(10,3) DEFAULT NULL COMMENT '抓取时间点（秒）',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_task_page` (`task_id`,`page_no`,`tenant_id`) USING BTREE,
  KEY `idx_course_id` (`course_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='PPT页级结果表';

/* F8 PPT页与视频时间锚点 */
DROP TABLE IF EXISTS `t_ppt_video_anchor`;
CREATE TABLE `t_ppt_video_anchor` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `task_id` varchar(64) NOT NULL COMMENT '分析任务ID',
  `course_id` bigint(20) DEFAULT NULL COMMENT '课程id',
  `page_no` int(11) NOT NULL COMMENT 'PPT页码',
  `video_second` decimal(10,3) NOT NULL COMMENT '视频时间秒',
  `confidence` decimal(5,2) DEFAULT NULL COMMENT '匹配置信度',
  `source` varchar(32) DEFAULT NULL COMMENT '来源 asr/vision/manual',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_task_page` (`task_id`,`page_no`) USING BTREE,
  KEY `idx_task_second` (`task_id`,`video_second`) USING BTREE,
  KEY `idx_course_id` (`course_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='PPT页与视频锚点映射表';

