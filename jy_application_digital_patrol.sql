/*
 Navicat Premium Dump SQL

 Source Server         : seacraft
 Source Server Type    : MySQL
 Source Server Version : 50744 (5.7.44-log)
 Source Host           : 10.80.6.54:3306
 Source Schema         : jy_application_digital_patrol

 Target Server Type    : MySQL
 Target Server Version : 50744 (5.7.44-log)
 File Encoding         : 65001

 Date: 21/04/2026 11:31:02
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for QRTZ_BLOB_TRIGGERS
-- ----------------------------
DROP TABLE IF EXISTS `QRTZ_BLOB_TRIGGERS`;
CREATE TABLE `QRTZ_BLOB_TRIGGERS` (
  `SCHED_NAME` varchar(120) NOT NULL COMMENT '调度器名称',
  `TRIGGER_NAME` varchar(190) NOT NULL COMMENT '触发器名称',
  `TRIGGER_GROUP` varchar(190) NOT NULL COMMENT '触发器组',
  `BLOB_DATA` blob COMMENT 'Blob数据',
  PRIMARY KEY (`SCHED_NAME`,`TRIGGER_NAME`,`TRIGGER_GROUP`) USING BTREE,
  KEY `IDX_QRTZ_BLOB_TRIGGERS_SCHED_NAME` (`SCHED_NAME`,`TRIGGER_NAME`,`TRIGGER_GROUP`) USING BTREE,
  CONSTRAINT `QRTZ_BLOB_TRIGGERS_ibfk_1` FOREIGN KEY (`SCHED_NAME`, `TRIGGER_NAME`, `TRIGGER_GROUP`) REFERENCES `QRTZ_TRIGGERS` (`SCHED_NAME`, `TRIGGER_NAME`, `TRIGGER_GROUP`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='Quartz Blob触发器表';

-- ----------------------------
-- Table structure for QRTZ_CALENDARS
-- ----------------------------
DROP TABLE IF EXISTS `QRTZ_CALENDARS`;
CREATE TABLE `QRTZ_CALENDARS` (
  `SCHED_NAME` varchar(120) NOT NULL COMMENT '调度器名称',
  `CALENDAR_NAME` varchar(190) NOT NULL COMMENT '日历名称',
  `CALENDAR` blob NOT NULL COMMENT '日历数据',
  PRIMARY KEY (`SCHED_NAME`,`CALENDAR_NAME`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='Quartz日历表';

-- ----------------------------
-- Table structure for QRTZ_CRON_TRIGGERS
-- ----------------------------
DROP TABLE IF EXISTS `QRTZ_CRON_TRIGGERS`;
CREATE TABLE `QRTZ_CRON_TRIGGERS` (
  `SCHED_NAME` varchar(120) NOT NULL COMMENT '调度器名称',
  `TRIGGER_NAME` varchar(190) NOT NULL COMMENT '触发器名称',
  `TRIGGER_GROUP` varchar(190) NOT NULL COMMENT '触发器组',
  `CRON_EXPRESSION` varchar(120) NOT NULL COMMENT 'Cron表达式',
  `TIME_ZONE_ID` varchar(80) DEFAULT NULL COMMENT '时区',
  PRIMARY KEY (`SCHED_NAME`,`TRIGGER_NAME`,`TRIGGER_GROUP`) USING BTREE,
  CONSTRAINT `QRTZ_CRON_TRIGGERS_ibfk_1` FOREIGN KEY (`SCHED_NAME`, `TRIGGER_NAME`, `TRIGGER_GROUP`) REFERENCES `QRTZ_TRIGGERS` (`SCHED_NAME`, `TRIGGER_NAME`, `TRIGGER_GROUP`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='Quartz Cron触发器表';

-- ----------------------------
-- Table structure for QRTZ_FIRED_TRIGGERS
-- ----------------------------
DROP TABLE IF EXISTS `QRTZ_FIRED_TRIGGERS`;
CREATE TABLE `QRTZ_FIRED_TRIGGERS` (
  `SCHED_NAME` varchar(120) NOT NULL COMMENT '调度器名称',
  `ENTRY_ID` varchar(95) NOT NULL COMMENT '条目ID',
  `TRIGGER_NAME` varchar(190) NOT NULL COMMENT '触发器名称',
  `TRIGGER_GROUP` varchar(190) NOT NULL COMMENT '触发器组',
  `INSTANCE_NAME` varchar(190) NOT NULL COMMENT '实例名称',
  `FIRED_TIME` bigint(13) NOT NULL COMMENT '触发时间',
  `SCHED_TIME` bigint(13) NOT NULL COMMENT '调度时间',
  `PRIORITY` int(11) NOT NULL COMMENT '优先级',
  `STATE` varchar(16) NOT NULL COMMENT '状态',
  `JOB_NAME` varchar(190) DEFAULT NULL COMMENT '任务名称',
  `JOB_GROUP` varchar(190) DEFAULT NULL COMMENT '任务组',
  `IS_NONCONCURRENT` varchar(1) DEFAULT NULL COMMENT '是否非并发',
  `REQUESTS_RECOVERY` varchar(1) DEFAULT NULL COMMENT '是否请求恢复',
  PRIMARY KEY (`SCHED_NAME`,`ENTRY_ID`) USING BTREE,
  KEY `IDX_QRTZ_FT_TRIG_INST_NAME` (`SCHED_NAME`,`INSTANCE_NAME`) USING BTREE,
  KEY `IDX_QRTZ_FT_INST_JOB_REQ_RCVRY` (`SCHED_NAME`,`INSTANCE_NAME`,`REQUESTS_RECOVERY`) USING BTREE,
  KEY `IDX_QRTZ_FT_J_G` (`SCHED_NAME`,`JOB_NAME`,`JOB_GROUP`) USING BTREE,
  KEY `IDX_QRTZ_FT_JG` (`SCHED_NAME`,`JOB_GROUP`) USING BTREE,
  KEY `IDX_QRTZ_FT_T_G` (`SCHED_NAME`,`TRIGGER_NAME`,`TRIGGER_GROUP`) USING BTREE,
  KEY `IDX_QRTZ_FT_TG` (`SCHED_NAME`,`TRIGGER_GROUP`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='Quartz已触发的触发器表';

-- ----------------------------
-- Table structure for QRTZ_JOB_DETAILS
-- ----------------------------
DROP TABLE IF EXISTS `QRTZ_JOB_DETAILS`;
CREATE TABLE `QRTZ_JOB_DETAILS` (
  `SCHED_NAME` varchar(120) NOT NULL COMMENT '调度器名称',
  `JOB_NAME` varchar(190) NOT NULL COMMENT '任务名称',
  `JOB_GROUP` varchar(190) NOT NULL COMMENT '任务组',
  `DESCRIPTION` varchar(250) DEFAULT NULL COMMENT '任务描述',
  `JOB_CLASS_NAME` varchar(250) NOT NULL COMMENT '任务类全名',
  `IS_DURABLE` varchar(1) NOT NULL COMMENT '是否持久化',
  `IS_NONCONCURRENT` varchar(1) NOT NULL COMMENT '是否非并发执行',
  `IS_UPDATE_DATA` varchar(1) NOT NULL COMMENT '是否更新数据',
  `REQUESTS_RECOVERY` varchar(1) NOT NULL COMMENT '是否请求恢复',
  `JOB_DATA` blob COMMENT '任务数据',
  PRIMARY KEY (`SCHED_NAME`,`JOB_NAME`,`JOB_GROUP`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='Quartz任务详情表';

-- ----------------------------
-- Table structure for QRTZ_LOCKS
-- ----------------------------
DROP TABLE IF EXISTS `QRTZ_LOCKS`;
CREATE TABLE `QRTZ_LOCKS` (
  `SCHED_NAME` varchar(120) NOT NULL COMMENT '调度器名称',
  `LOCK_NAME` varchar(40) NOT NULL COMMENT '锁名称',
  PRIMARY KEY (`SCHED_NAME`,`LOCK_NAME`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='Quartz锁表';

-- ----------------------------
-- Table structure for QRTZ_PAUSED_TRIGGER_GRPS
-- ----------------------------
DROP TABLE IF EXISTS `QRTZ_PAUSED_TRIGGER_GRPS`;
CREATE TABLE `QRTZ_PAUSED_TRIGGER_GRPS` (
  `SCHED_NAME` varchar(120) NOT NULL COMMENT '调度器名称',
  `TRIGGER_GROUP` varchar(190) NOT NULL COMMENT '触发器组',
  PRIMARY KEY (`SCHED_NAME`,`TRIGGER_GROUP`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='Quartz暂停的触发器组表';

-- ----------------------------
-- Table structure for QRTZ_SCHEDULER_STATE
-- ----------------------------
DROP TABLE IF EXISTS `QRTZ_SCHEDULER_STATE`;
CREATE TABLE `QRTZ_SCHEDULER_STATE` (
  `SCHED_NAME` varchar(120) NOT NULL COMMENT '调度器名称',
  `INSTANCE_NAME` varchar(190) NOT NULL COMMENT '实例名称',
  `LAST_CHECKIN_TIME` bigint(13) NOT NULL COMMENT '最后签到时间',
  `CHECKIN_INTERVAL` bigint(13) NOT NULL COMMENT '签到间隔',
  PRIMARY KEY (`SCHED_NAME`,`INSTANCE_NAME`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='Quartz调度器状态表';

-- ----------------------------
-- Table structure for QRTZ_SIMPLE_TRIGGERS
-- ----------------------------
DROP TABLE IF EXISTS `QRTZ_SIMPLE_TRIGGERS`;
CREATE TABLE `QRTZ_SIMPLE_TRIGGERS` (
  `SCHED_NAME` varchar(120) NOT NULL COMMENT '调度器名称',
  `TRIGGER_NAME` varchar(190) NOT NULL COMMENT '触发器名称',
  `TRIGGER_GROUP` varchar(190) NOT NULL COMMENT '触发器组',
  `REPEAT_COUNT` bigint(7) NOT NULL COMMENT '重复次数',
  `REPEAT_INTERVAL` bigint(12) NOT NULL COMMENT '重复间隔',
  `TIMES_TRIGGERED` bigint(10) NOT NULL COMMENT '已触发次数',
  PRIMARY KEY (`SCHED_NAME`,`TRIGGER_NAME`,`TRIGGER_GROUP`) USING BTREE,
  CONSTRAINT `QRTZ_SIMPLE_TRIGGERS_ibfk_1` FOREIGN KEY (`SCHED_NAME`, `TRIGGER_NAME`, `TRIGGER_GROUP`) REFERENCES `QRTZ_TRIGGERS` (`SCHED_NAME`, `TRIGGER_NAME`, `TRIGGER_GROUP`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='Quartz简单触发器表';

-- ----------------------------
-- Table structure for QRTZ_SIMPROP_TRIGGERS
-- ----------------------------
DROP TABLE IF EXISTS `QRTZ_SIMPROP_TRIGGERS`;
CREATE TABLE `QRTZ_SIMPROP_TRIGGERS` (
  `SCHED_NAME` varchar(120) NOT NULL COMMENT '调度器名称',
  `TRIGGER_NAME` varchar(190) NOT NULL COMMENT '触发器名称',
  `TRIGGER_GROUP` varchar(190) NOT NULL COMMENT '触发器组',
  `STR_PROP_1` varchar(512) DEFAULT NULL COMMENT '字符串属性1',
  `STR_PROP_2` varchar(512) DEFAULT NULL COMMENT '字符串属性2',
  `STR_PROP_3` varchar(512) DEFAULT NULL COMMENT '字符串属性3',
  `INT_PROP_1` int(11) DEFAULT NULL COMMENT '整数属性1',
  `INT_PROP_2` int(11) DEFAULT NULL COMMENT '整数属性2',
  `LONG_PROP_1` bigint(20) DEFAULT NULL COMMENT '长整数属性1',
  `LONG_PROP_2` bigint(20) DEFAULT NULL COMMENT '长整数属性2',
  `DEC_PROP_1` decimal(13,4) DEFAULT NULL COMMENT '小数属性1',
  `DEC_PROP_2` decimal(13,4) DEFAULT NULL COMMENT '小数属性2',
  `BOOL_PROP_1` varchar(1) DEFAULT NULL COMMENT '布尔属性1',
  `BOOL_PROP_2` varchar(1) DEFAULT NULL COMMENT '布尔属性2',
  PRIMARY KEY (`SCHED_NAME`,`TRIGGER_NAME`,`TRIGGER_GROUP`) USING BTREE,
  CONSTRAINT `QRTZ_SIMPROP_TRIGGERS_ibfk_1` FOREIGN KEY (`SCHED_NAME`, `TRIGGER_NAME`, `TRIGGER_GROUP`) REFERENCES `QRTZ_TRIGGERS` (`SCHED_NAME`, `TRIGGER_NAME`, `TRIGGER_GROUP`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='Quartz简单属性触发器表';

-- ----------------------------
-- Table structure for QRTZ_TRIGGERS
-- ----------------------------
DROP TABLE IF EXISTS `QRTZ_TRIGGERS`;
CREATE TABLE `QRTZ_TRIGGERS` (
  `SCHED_NAME` varchar(120) NOT NULL COMMENT '调度器名称',
  `TRIGGER_NAME` varchar(190) NOT NULL COMMENT '触发器名称',
  `TRIGGER_GROUP` varchar(190) NOT NULL COMMENT '触发器组',
  `JOB_NAME` varchar(190) NOT NULL COMMENT '任务名称',
  `JOB_GROUP` varchar(190) NOT NULL COMMENT '任务组',
  `DESCRIPTION` varchar(250) DEFAULT NULL COMMENT '触发器描述',
  `NEXT_FIRE_TIME` bigint(13) DEFAULT NULL COMMENT '下次触发时间',
  `PREV_FIRE_TIME` bigint(13) DEFAULT NULL COMMENT '上次触发时间',
  `PRIORITY` int(11) DEFAULT NULL COMMENT '优先级',
  `TRIGGER_STATE` varchar(16) NOT NULL COMMENT '触发器状态',
  `TRIGGER_TYPE` varchar(8) NOT NULL COMMENT '触发器类型',
  `START_TIME` bigint(13) NOT NULL COMMENT '开始时间',
  `END_TIME` bigint(13) DEFAULT NULL COMMENT '结束时间',
  `CALENDAR_NAME` varchar(190) DEFAULT NULL COMMENT '日历名称',
  `MISFIRE_INSTR` smallint(2) DEFAULT NULL COMMENT '错过触发策略',
  `JOB_DATA` blob COMMENT '任务数据',
  PRIMARY KEY (`SCHED_NAME`,`TRIGGER_NAME`,`TRIGGER_GROUP`) USING BTREE,
  KEY `IDX_QRTZ_T_J` (`SCHED_NAME`,`JOB_NAME`,`JOB_GROUP`) USING BTREE,
  KEY `IDX_QRTZ_T_JG` (`SCHED_NAME`,`JOB_GROUP`) USING BTREE,
  KEY `IDX_QRTZ_T_C` (`SCHED_NAME`,`CALENDAR_NAME`) USING BTREE,
  KEY `IDX_QRTZ_T_G` (`SCHED_NAME`,`TRIGGER_GROUP`) USING BTREE,
  KEY `IDX_QRTZ_T_STATE` (`SCHED_NAME`,`TRIGGER_STATE`) USING BTREE,
  KEY `IDX_QRTZ_T_N_STATE` (`SCHED_NAME`,`TRIGGER_NAME`,`TRIGGER_GROUP`,`TRIGGER_STATE`) USING BTREE,
  KEY `IDX_QRTZ_T_N_G_STATE` (`SCHED_NAME`,`TRIGGER_GROUP`,`TRIGGER_STATE`) USING BTREE,
  KEY `IDX_QRTZ_T_NEXT_FIRE_TIME` (`SCHED_NAME`,`NEXT_FIRE_TIME`) USING BTREE,
  KEY `IDX_QRTZ_T_NFT_ST` (`SCHED_NAME`,`TRIGGER_STATE`,`NEXT_FIRE_TIME`) USING BTREE,
  KEY `IDX_QRTZ_T_NFT_MISFIRE` (`SCHED_NAME`,`MISFIRE_INSTR`,`NEXT_FIRE_TIME`) USING BTREE,
  KEY `IDX_QRTZ_T_NFT_ST_MISFIRE` (`SCHED_NAME`,`MISFIRE_INSTR`,`NEXT_FIRE_TIME`,`TRIGGER_STATE`) USING BTREE,
  KEY `IDX_QRTZ_T_NFT_ST_MISFIRE_GRP` (`SCHED_NAME`,`MISFIRE_INSTR`,`NEXT_FIRE_TIME`,`TRIGGER_GROUP`,`TRIGGER_STATE`) USING BTREE,
  CONSTRAINT `QRTZ_TRIGGERS_ibfk_1` FOREIGN KEY (`SCHED_NAME`, `JOB_NAME`, `JOB_GROUP`) REFERENCES `QRTZ_JOB_DETAILS` (`SCHED_NAME`, `JOB_NAME`, `JOB_GROUP`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='Quartz触发器表';

-- ----------------------------
-- Table structure for flyway_schema_history
-- ----------------------------
DROP TABLE IF EXISTS `flyway_schema_history`;
CREATE TABLE `flyway_schema_history` (
  `installed_rank` int(11) NOT NULL,
  `version` varchar(50) DEFAULT NULL,
  `description` varchar(200) NOT NULL,
  `type` varchar(20) NOT NULL,
  `script` varchar(1000) NOT NULL,
  `checksum` int(11) DEFAULT NULL,
  `installed_by` varchar(100) NOT NULL,
  `installed_on` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `execution_time` int(11) NOT NULL,
  `success` tinyint(1) NOT NULL,
  PRIMARY KEY (`installed_rank`) USING BTREE,
  KEY `flyway_schema_history_s_idx` (`success`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;

-- ----------------------------
-- Table structure for t_ai_coverage_daily
-- ----------------------------
DROP TABLE IF EXISTS `t_ai_coverage_daily`;
CREATE TABLE `t_ai_coverage_daily` (
  `id` bigint(20) NOT NULL COMMENT ' 主键ID（雪花算法生成）',
  `detection_date` date NOT NULL COMMENT '检测日期',
  `classroom_count` int(11) DEFAULT '0' COMMENT '教室总数',
  `ai_classroom_count` int(11) DEFAULT '0' COMMENT 'AI分析教室数',
  `teacher_count` int(11) DEFAULT '0' COMMENT '教师总数',
  `ai_teacher_count` int(11) DEFAULT '0' COMMENT 'AI分析教师数',
  `subject_count` int(11) DEFAULT '0' COMMENT '科目总数',
  `ai_subject_count` int(11) DEFAULT '0' COMMENT 'AI分析科目数',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT ' 最后修改时间 ',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_detection_date` (`detection_date`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI覆盖率统计-日汇总表';

-- ----------------------------
-- Table structure for t_ai_coverage_org_detail
-- ----------------------------
DROP TABLE IF EXISTS `t_ai_coverage_org_detail`;
CREATE TABLE `t_ai_coverage_org_detail` (
  `id` bigint(20) NOT NULL COMMENT ' 主键ID（雪花算法生成）',
  `summary_id` bigint(20) NOT NULL COMMENT '日汇总表ID',
  `detection_date` date NOT NULL COMMENT '检测日期',
  `org_id` bigint(20) NOT NULL COMMENT '院系ID',
  `org_code` varchar(50) DEFAULT NULL COMMENT '院系编码',
  `org_name` varchar(200) DEFAULT NULL COMMENT '院系名称',
  `subject_coverage_rate` decimal(5,2) DEFAULT '0.00' COMMENT '科目覆盖率(%)',
  `teacher_coverage_rate` decimal(5,2) DEFAULT '0.00' COMMENT '教师覆盖率(%)',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT ' 最后修改时间 ',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_detection_date` (`detection_date`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_org_id` (`detection_date`,`delete_flag`,`tenant_id`,`org_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI覆盖率统计-院系明细表';

-- ----------------------------
-- Table structure for t_ai_statistics_settings
-- ----------------------------
DROP TABLE IF EXISTS `t_ai_statistics_settings`;
CREATE TABLE `t_ai_statistics_settings` (
  `id` bigint(20) NOT NULL COMMENT '主键',
  `type` varchar(50) DEFAULT NULL COMMENT '类型（学情、教情等）',
  `data_name` varchar(100) DEFAULT NULL COMMENT '数据名称',
  `display_name` varchar(100) DEFAULT NULL COMMENT '显示名称',
  `code` varchar(100) DEFAULT NULL COMMENT '数据编码',
  `description` varchar(500) DEFAULT NULL COMMENT '描述',
  `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态（0：禁用，1：启用）',
  `sort` int(11) DEFAULT NULL COMMENT '排序',
  `extra_json` varchar(500) DEFAULT NULL COMMENT '额外字段（JSON格式）',
  `indicator_code` varchar(100) DEFAULT NULL COMMENT '预警指标code',
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
  KEY `idx_type` (`type`) USING BTREE,
  KEY `idx_code` (`code`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI统计设置表';

-- ----------------------------
-- Table structure for t_async_import_export_task
-- ----------------------------
DROP TABLE IF EXISTS `t_async_import_export_task`;
CREATE TABLE `t_async_import_export_task` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法）',
  `task_id` varchar(64) NOT NULL COMMENT '任务ID',
  `task_type` tinyint(4) NOT NULL COMMENT '任务类型（1-导出 2-导入）',
  `task_status` tinyint(4) NOT NULL DEFAULT '0' COMMENT '任务状态（0-待处理，1-处理中，2-完成，3-失败）',
  `progress` int(11) NOT NULL DEFAULT '0' COMMENT '任务进度（0-100）',
  `file_name` varchar(255) DEFAULT NULL COMMENT '文件名称',
  `file_path` varchar(512) DEFAULT NULL COMMENT '文件路径',
  `file_size` bigint(20) DEFAULT NULL COMMENT '文件大小（字节）',
  `error_msg` text COMMENT '错误信息JSON',
  `total_count` int(11) NOT NULL DEFAULT '0' COMMENT '总记录数',
  `success_count` int(11) NOT NULL DEFAULT '0' COMMENT '成功记录数',
  `fail_count` int(11) NOT NULL DEFAULT '0' COMMENT '失败记录数',
  `start_time` datetime DEFAULT NULL COMMENT '开始时间',
  `end_time` datetime DEFAULT NULL COMMENT '结束时间',
  `expire_time` datetime DEFAULT NULL COMMENT '过期时间',
  `download_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '下载标记（0-否 1-是）',
  `timeout_minutes` int(11) NOT NULL DEFAULT '30' COMMENT '任务超时时间（分钟）',
  `retention_hours` int(11) NOT NULL DEFAULT '24' COMMENT '文件保留时长（小时）',
  `tenant_id` varchar(50) DEFAULT NULL COMMENT '租户ID',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(64) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `last_modified_by` varchar(64) DEFAULT NULL COMMENT '更新人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标记',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_async_task_id` (`task_id`) USING BTREE,
  KEY `idx_async_status` (`task_status`) USING BTREE,
  KEY `idx_async_created` (`created_date_time`) USING BTREE,
  KEY `idx_async_tenant` (`tenant_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='异步导入导出任务表';

-- ----------------------------
-- Table structure for t_config_data
-- ----------------------------
DROP TABLE IF EXISTS `t_config_data`;
CREATE TABLE `t_config_data` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `config_key` varchar(255) CHARACTER SET utf8mb4 DEFAULT NULL COMMENT '配置key',
  `config_value` text CHARACTER SET utf8mb4 COMMENT '配置值',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) CHARACTER SET utf8mb4 DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) CHARACTER SET utf8mb4 DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) CHARACTER SET utf8mb4 NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_config_key` (`config_key`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_german2_ci ROW_FORMAT=DYNAMIC COMMENT='配置表';

-- ----------------------------
-- Table structure for t_course_date_slot_statistics
-- ----------------------------
DROP TABLE IF EXISTS `t_course_date_slot_statistics`;
CREATE TABLE `t_course_date_slot_statistics` (
  `id` bigint(20) NOT NULL COMMENT ' 主键ID（雪花算法生成）',
  `detection_date` datetime DEFAULT NULL COMMENT '检测日期',
  `leti_number` int(11) NOT NULL COMMENT '节次',
  `total_count` int(11) DEFAULT '0' COMMENT '总共节次数',
  `abnormal_count` int(11) DEFAULT '0' COMMENT '异常节次数',
  `normal_courses` int(11) DEFAULT '0' COMMENT '正常节次数',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT ' 最后修改时间 ',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_detection_date` (`detection_date`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_detection_date_leti_number` (`detection_date`,`leti_number`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='日期节次开课数量统计表';

-- ----------------------------
-- Table structure for t_device_bind_record_plan
-- ----------------------------
DROP TABLE IF EXISTS `t_device_bind_record_plan`;
CREATE TABLE `t_device_bind_record_plan` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `plan_id` varchar(255) DEFAULT NULL COMMENT '媒体录像计划id',
  `gb_id` varchar(255) DEFAULT NULL COMMENT '设备国标id',
  `camp_id` bigint(20) DEFAULT NULL COMMENT '校区id',
  `clro_id` bigint(20) NOT NULL COMMENT '教室id',
  `clro_name` varchar(255) NOT NULL COMMENT '教室名称',
  `chn_name` varchar(255) NOT NULL COMMENT '通道名称',
  `record_plan_status` tinyint(4) DEFAULT NULL COMMENT '录像计划状态 1:正常 0:禁用',
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
  KEY `idx_gb_id_paln_key` (`plan_id`,`gb_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='设备绑定录像计划表';

-- ----------------------------
-- Table structure for t_device_status_check
-- ----------------------------
DROP TABLE IF EXISTS `t_device_status_check`;
CREATE TABLE `t_device_status_check` (
  `id` bigint(20) NOT NULL COMMENT '主键ID',
  `clro_id` bigint(20) NOT NULL COMMENT '教室id',
  `channel_gb_id` varchar(255) DEFAULT NULL COMMENT '设备通道国标id',
  `channel_name` varchar(255) DEFAULT NULL COMMENT '设备通道名称',
  `online_status` tinyint(4) DEFAULT NULL COMMENT '在线状态；0-离线 1-在线',
  `ai_server_status` tinyint(4) DEFAULT NULL COMMENT 'AI服务状态；0-异常 1-正常',
  `quality_check_types` varchar(512) DEFAULT NULL COMMENT '画质异常检测类型，多个以逗号隔开',
  `detection_time` datetime DEFAULT NULL COMMENT '检测时间',
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
  KEY `idx_clro_id` (`clro_id`) USING BTREE,
  KEY `idx_channel_gb_id` (`channel_gb_id`) USING BTREE,
  KEY `idx_detection_time` (`detection_time`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='设备状态检查表';

-- ----------------------------
-- Table structure for t_media_video_record
-- ----------------------------
DROP TABLE IF EXISTS `t_media_video_record`;
CREATE TABLE `t_media_video_record` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `record_id` varchar(255) DEFAULT NULL COMMENT '录像文件id',
  `vod_start_time` datetime DEFAULT NULL COMMENT '点播开始时间',
  `vod_end_time` datetime DEFAULT NULL COMMENT '点播结束时间',
  `file_name` varchar(255) DEFAULT NULL COMMENT '包含路径的文件名称',
  `file_url` varchar(255) DEFAULT NULL COMMENT '文件的播放地址',
  `gb_id` varchar(255) DEFAULT NULL COMMENT '设备通道的国标id',
  `rec_size` bigint(20) DEFAULT '0' COMMENT '录像文件大小，单位Kb',
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
  KEY `idx_gb_record_id_key` (`gb_id`,`vod_start_time`,`vod_end_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='媒体录像记录表';

-- ----------------------------
-- Table structure for t_ops_check_device_result
-- ----------------------------
DROP TABLE IF EXISTS `t_ops_check_device_result`;
CREATE TABLE `t_ops_check_device_result` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `check_plan_id` bigint(20) DEFAULT NULL COMMENT '巡检计划id',
  `check_plan_name` varchar(255) DEFAULT NULL COMMENT '巡检计划名称',
  `check_plan_type` tinyint(4) DEFAULT NULL COMMENT '巡检计划类型 1-设备在线检测 2-教室音频检测',
  `freq_type` tinyint(4) DEFAULT NULL COMMENT '巡检频率类型 1-日 2-周 3-月',
  `result_status` tinyint(4) DEFAULT NULL COMMENT '计划结果状态 0-进行中 1-成功 2-异常',
  `check_error_type` tinyint(4) DEFAULT NULL COMMENT '检查失败类型 1-服务调用异常 99-其他',
  `check_error_msg` varchar(255) DEFAULT NULL COMMENT '检查失败说明',
  `execute_start_time` datetime DEFAULT NULL COMMENT '巡检执行开始时间',
  `execute_end_time` datetime DEFAULT NULL COMMENT '巡检执行结束时间',
  `has_image_quality_result` tinyint(4) DEFAULT '0' COMMENT '是否有图片质量检测结果 0-无 1-有',
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
  KEY `idx_check_plan_id` (`check_plan_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课-运维-巡检计划-设备在线结果表';

-- ----------------------------
-- Table structure for t_ops_check_device_result_detail
-- ----------------------------
DROP TABLE IF EXISTS `t_ops_check_device_result_detail`;
CREATE TABLE `t_ops_check_device_result_detail` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `check_device_result_id` bigint(20) DEFAULT NULL COMMENT '设备在线结果id',
  `clro_id` bigint(20) DEFAULT NULL COMMENT '教室id',
  `clro_name` varchar(255) DEFAULT NULL COMMENT '教室名称',
  `build_id` bigint(20) DEFAULT NULL COMMENT '教学楼Id',
  `build_name` varchar(255) DEFAULT NULL COMMENT '教学楼名称',
  `view_num` tinyint(4) DEFAULT NULL COMMENT '视角编号（1:教师1;2:教师2;3:学生1;4:学生2;5:PPT;6:电子白板7:合成通道）',
  `chan_gbid_main` varchar(50) DEFAULT NULL COMMENT '主流通道国标id',
  `chan_name_main` varchar(50) DEFAULT NULL COMMENT '主流通道名称',
  `online_flag` tinyint(4) DEFAULT NULL COMMENT '是否在线 0-离线 1-在线',
  `bad_image_quality_flag` tinyint(4) DEFAULT NULL COMMENT '是否存在画质差 0-正常 1-异常',
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
  KEY `idx_check_device_result_id` (`check_device_result_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课-运维-巡检计划-设备在线结果明细表';

-- ----------------------------
-- Table structure for t_ops_check_device_result_detail_quality
-- ----------------------------
DROP TABLE IF EXISTS `t_ops_check_device_result_detail_quality`;
CREATE TABLE `t_ops_check_device_result_detail_quality` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `device_result_detail_id` bigint(20) DEFAULT NULL COMMENT '设备在线结果明细id',
  `quality_check_type` tinyint(4) DEFAULT NULL COMMENT '质量检测类型 1-图像模糊 2-遮挡 3-信号丢失 4-画面歪 5-丢帧 6-偏色 7-亮度异常 8-镜头抖动 9-噪声 10-图像黑白 11-对比异常 12-场景变换 13-视频剧变 14-干扰',
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
  KEY `idx_device_result_detail_id` (`device_result_detail_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课-运维-巡检计划-设备在线-画质检测异常表';

-- ----------------------------
-- Table structure for t_ops_check_plan
-- ----------------------------
DROP TABLE IF EXISTS `t_ops_check_plan`;
CREATE TABLE `t_ops_check_plan` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `check_plan_name` varchar(255) DEFAULT NULL COMMENT '巡检计划名称',
  `check_plan_type` tinyint(4) DEFAULT NULL COMMENT '巡检计划类型 1-设备在线检测 2-教室音频检测',
  `freq_start_date` datetime DEFAULT NULL COMMENT '巡检频率开始日期',
  `freq_end_date` datetime DEFAULT NULL COMMENT '巡检频率结束日期',
  `freq_type` tinyint(4) DEFAULT NULL COMMENT '巡检频率类型 1-日 2-周 3-月',
  `freq_type_detail` varchar(255) DEFAULT NULL COMMENT '巡检频率时间详情 多个用,隔开,日:为空 周:1~7 月:1~31',
  `freq_execute_time` varchar(50) DEFAULT NULL COMMENT '巡检频率执行时间 示例：07:00:00',
  `enable_status` tinyint(4) DEFAULT NULL COMMENT '计划是否启用 0-禁用 1-启用',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课-运维-巡检计划表';

-- ----------------------------
-- Table structure for t_ops_check_plan_classroom
-- ----------------------------
DROP TABLE IF EXISTS `t_ops_check_plan_classroom`;
CREATE TABLE `t_ops_check_plan_classroom` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `check_plan_id` bigint(20) DEFAULT NULL COMMENT '巡检计划id',
  `clro_id` bigint(20) DEFAULT NULL COMMENT '教室id',
  `clro_name` varchar(255) DEFAULT NULL COMMENT '教室名称',
  `build_id` bigint(20) DEFAULT NULL COMMENT '教学楼Id',
  `build_name` varchar(255) DEFAULT NULL COMMENT '教学楼名称',
  `campus_id` bigint(20) DEFAULT NULL COMMENT '校区id',
  `campus_name` varchar(255) DEFAULT NULL COMMENT '校区名称',
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
  KEY `idx_check_plan_id` (`check_plan_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课-运维-巡检计划教室表';

-- ----------------------------
-- Table structure for t_ops_check_plan_quality_config
-- ----------------------------
DROP TABLE IF EXISTS `t_ops_check_plan_quality_config`;
CREATE TABLE `t_ops_check_plan_quality_config` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `check_plan_id` bigint(20) DEFAULT NULL COMMENT '巡检计划id',
  `view_num` tinyint(4) DEFAULT NULL COMMENT '视角编号（1:教师1;2:教师2;3:学生1;4:学生2;5:PPT;6:电子白板7:合成通道）',
  `quality_check_type` tinyint(4) DEFAULT NULL COMMENT '质量检测类型 1-图像模糊 2-遮挡 3-信号丢失 4-画面歪 5-丢帧 6-偏色 7-亮度异常 8-镜头抖动 9-噪声 10-图像黑白 11-对比异常 12-场景变换 13-视频剧变 14-干扰',
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
  KEY `idx_check_plan_id` (`check_plan_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课-运维-巡检计划质量配置表';

-- ----------------------------
-- Table structure for t_ops_video_history_missing_time
-- ----------------------------
DROP TABLE IF EXISTS `t_ops_video_history_missing_time`;
CREATE TABLE `t_ops_video_history_missing_time` (
  `id` bigint(20) NOT NULL COMMENT '主键ID',
  `plan_time_id` bigint(20) NOT NULL COMMENT '录像历史计划时间主键ID',
  `missing_start_time` datetime DEFAULT NULL COMMENT '录像缺失开始时间',
  `missing_end_time` datetime DEFAULT NULL COMMENT '录像缺失结束时间',
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
  KEY `idx_plan_time_id_missing_time` (`plan_time_id`,`missing_start_time`,`missing_end_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='录像缺失表';

-- ----------------------------
-- Table structure for t_ops_video_history_monitor_record
-- ----------------------------
DROP TABLE IF EXISTS `t_ops_video_history_monitor_record`;
CREATE TABLE `t_ops_video_history_monitor_record` (
  `id` bigint(20) NOT NULL COMMENT '主键ID',
  `campus_id` bigint(20) DEFAULT NULL COMMENT '校区id',
  `campus_name` varchar(255) DEFAULT NULL COMMENT '校区名称',
  `build_id` bigint(20) DEFAULT NULL COMMENT '教学楼id',
  `build_name` varchar(255) DEFAULT NULL COMMENT '教学楼名称',
  `clro_id` bigint(20) DEFAULT NULL COMMENT '教室id',
  `clro_name` varchar(255) DEFAULT NULL COMMENT '教室名称',
  `gb_id` varchar(255) DEFAULT NULL COMMENT '设备国标id',
  `plan_id` varchar(255) DEFAULT NULL COMMENT '媒体录像计划id',
  `video_date` date DEFAULT NULL COMMENT '录像日期',
  `channel_name` varchar(255) DEFAULT NULL COMMENT '通道名称',
  `device_view_num` int(11) DEFAULT NULL COMMENT '视角编号（1:教师1;2:教师2;3:学生1;4:学生2;5:PPT;6:电子白板7:合成通道）',
  `abnormal_type` tinyint(4) DEFAULT NULL COMMENT '异常类型；0-未监控，1-录像完整，2-录像缺失，3-无录像',
  `affect_record` tinyint(4) DEFAULT NULL COMMENT '影响录制；1-影响，2-不影响',
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
  KEY `idx_clro_id` (`clro_id`) USING BTREE,
  KEY `idx_video_date` (`video_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='录像历史监控记录';

-- ----------------------------
-- Table structure for t_ops_video_history_plan_time
-- ----------------------------
DROP TABLE IF EXISTS `t_ops_video_history_plan_time`;
CREATE TABLE `t_ops_video_history_plan_time` (
  `id` bigint(20) NOT NULL COMMENT '主键ID',
  `monitor_record_id` bigint(20) NOT NULL COMMENT '录像历史监控记录表ID',
  `video_date` date DEFAULT NULL COMMENT '录像日期',
  `plan_start_time` datetime DEFAULT NULL COMMENT '录像计划开始时间',
  `plan_end_time` datetime DEFAULT NULL COMMENT '录像计划结束时间',
  `abnormal_type` tinyint(4) DEFAULT NULL COMMENT '异常类型；0-未监控，1-录像完整，2-录像缺失，3-无录像',
  `affect_record` tinyint(4) DEFAULT NULL COMMENT '影响录制；1-影响，2-不影响',
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
  KEY `idx_monitor_record_id_plan_time` (`monitor_record_id`,`plan_start_time`,`plan_end_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='录像历史计划时间表';

-- ----------------------------
-- Table structure for t_patrol_alarm_event
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_alarm_event`;
CREATE TABLE `t_patrol_alarm_event` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  `indicator_id` bigint(20) NOT NULL COMMENT '指标id',
  `alarm_frequency` int(11) DEFAULT NULL COMMENT '预警频率',
  `alarm_range_type` smallint(6) DEFAULT '0' COMMENT '预警区间类型：0 普通,1 按大课, 2 按节次',
  `class_from` int(11) DEFAULT NULL COMMENT '课程时段起点',
  `class_to` int(11) DEFAULT NULL COMMENT '课程时段终点',
  `course_time_status` smallint(6) DEFAULT NULL COMMENT '课程时间状态，1-课程开始前，2-课程开始后，3-课程结束前，4-课程结束后',
  `rules_json` json DEFAULT NULL COMMENT '规则内容',
  `alarm_desc` text COMMENT '提醒文案',
  `event_type` smallint(6) DEFAULT NULL COMMENT '事件类型 1学情 2教情 3 设备 4 空间',
  `effective_begin_time` datetime DEFAULT NULL COMMENT '生效开始时间',
  `effective_end_time` datetime DEFAULT NULL COMMENT '生效结束时间',
  `face_enable` smallint(6) DEFAULT '0' COMMENT '是否开启人脸识别',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_tenant_org_code` (`tenant_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2019016211064504323 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课告警事件表';

-- ----------------------------
-- Table structure for t_patrol_alarm_strategy
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_alarm_strategy`;
CREATE TABLE `t_patrol_alarm_strategy` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  `alarm_strategy_name` varchar(255) DEFAULT NULL COMMENT '策略名称',
  `alarm_enable` smallint(6) DEFAULT '0' COMMENT '是否开启 0 否  1 是',
  `alarm_desc` text COMMENT '说明',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_tenant_org_code` (`tenant_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2032029347893096451 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课告警策略表';

-- ----------------------------
-- Table structure for t_patrol_alarm_strategy_event_relation
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_alarm_strategy_event_relation`;
CREATE TABLE `t_patrol_alarm_strategy_event_relation` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  `alarm_strategy_id` bigint(20) DEFAULT NULL COMMENT '预警策略id',
  `alarm_event_id` bigint(20) DEFAULT NULL COMMENT '预警事件id',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_alarm_strategy_id` (`alarm_strategy_id`) USING BTREE,
  KEY `idx_alarm_event_id` (`alarm_event_id`) USING BTREE,
  KEY `idx_tenant_org_code` (`tenant_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2032029348002148355 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课告警策略事件关联表';

-- ----------------------------
-- Table structure for t_patrol_attendance_confirm_record
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_attendance_confirm_record`;
CREATE TABLE `t_patrol_attendance_confirm_record` (
  `id` bigint(20) NOT NULL COMMENT '主键',
  `course_id` bigint(20) DEFAULT NULL COMMENT '课程id',
  `confirm_time_type` tinyint(4) DEFAULT NULL COMMENT '确认时间类型 1-上课 2-下课',
  `teacher_face_info_id` bigint(20) DEFAULT NULL COMMENT '确认的老师人脸信息id',
  `other_face_flag` tinyint(4) DEFAULT NULL COMMENT '是否为非排课老师或代课 0-否 1-是',
  `warning_record_id` bigint(20) DEFAULT NULL COMMENT '关联的预警记录id',
  `confirm_result` tinyint(4) DEFAULT NULL COMMENT '确认结果 1-正常 2-异常 3-缺勤',
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
  KEY `idx_course_id` (`course_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课-出勤确认记录';

-- ----------------------------
-- Table structure for t_patrol_classroom_status
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_classroom_status`;
CREATE TABLE `t_patrol_classroom_status` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT ' 主键 ',
  `classroom_id` bigint(20) DEFAULT NULL COMMENT ' 教室id ',
  `has_people` smallint(6) DEFAULT '0' COMMENT ' 是否有人 0 无人 1有人 ',
  `tias_event_time` datetime DEFAULT NULL COMMENT ' tias事件时间 ',
  `tias_seat_num` int(11) DEFAULT NULL COMMENT ' tias座位数 ',
  `tias_people_num` int(11) DEFAULT NULL COMMENT ' tias就坐人数 ',
  `tias_seat_percent` decimal(20,2) DEFAULT NULL COMMENT ' tias就座率 ',
  `tias_free_percent` decimal(20,2) DEFAULT NULL COMMENT ' tias空闲率 ',
  `tias_people_num_chart` text COMMENT ' tias就坐人数图表 ',
  `tias_seat_percent_chart` text COMMENT ' tias就座率图表 ',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT ' 创建人id ',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT ' 更新人id ',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_classroom_id` (`classroom_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_has_people` (`has_people`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2016647483374698498 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课教室状态表';

-- ----------------------------
-- Table structure for t_patrol_classroom_user_attention
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_classroom_user_attention`;
CREATE TABLE `t_patrol_classroom_user_attention` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `user_id` bigint(20) DEFAULT NULL COMMENT '用户id',
  `clro_id` bigint(20) DEFAULT NULL COMMENT '教室id',
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
  KEY `idx_user_id` (`user_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课-用户关注教室表';

-- ----------------------------
-- Table structure for t_patrol_indicator_type
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_indicator_type`;
CREATE TABLE `t_patrol_indicator_type` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  `indicator_name` varchar(100) DEFAULT NULL COMMENT '指标名称',
  `indicator_code` varchar(100) DEFAULT NULL COMMENT '指标code',
  `event_type` smallint(6) DEFAULT NULL COMMENT '事件类型 1学情 2教情 3 设备 4 空间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_tenant_org_code` (`tenant_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=27 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='指标类型表';

-- ----------------------------
-- Table structure for t_patrol_lexicon_type
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_lexicon_type`;
CREATE TABLE `t_patrol_lexicon_type` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `lexicon_name` varchar(50) NOT NULL COMMENT '词库名称',
  `lexicon_code` varchar(50) NOT NULL COMMENT '词库编码',
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
  KEY `idx_tenant_id` (`tenant_id`) USING BTREE,
  KEY `idx_lexicon_name` (`lexicon_name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2033349801420349443 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='词库类别';

-- ----------------------------
-- Table structure for t_patrol_org_user_rel
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_org_user_rel`;
CREATE TABLE `t_patrol_org_user_rel` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `org_id` bigint(20) NOT NULL COMMENT '院系ID',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `user_code` varchar(50) NOT NULL COMMENT '用户code',
  `user_name` varchar(50) NOT NULL COMMENT '用户姓名',
  `user_org_id` bigint(20) NOT NULL COMMENT '用户所属院系ID',
  `user_org_code` varchar(50) NOT NULL COMMENT '用户所属院系code',
  `user_org_name` varchar(50) NOT NULL COMMENT '用户所属院系name',
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
  KEY `idx_org_id` (`org_id`) USING BTREE,
  KEY `idx_tenant_id` (`tenant_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2018519045290999810 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='院系与联络人关联表';

-- ----------------------------
-- Table structure for t_patrol_organization
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_organization`;
CREATE TABLE `t_patrol_organization` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `parent_id` bigint(20) DEFAULT NULL COMMENT '父级院系id',
  `org_id` bigint(20) NOT NULL COMMENT '院系id',
  `org_code` varchar(50) NOT NULL COMMENT '院系编码',
  `org_name` varchar(100) NOT NULL COMMENT '院系名称',
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
  KEY `idx_tenant_id` (`tenant_id`) USING BTREE,
  KEY `idx_org_name` (`org_name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2018498887918559235 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='开课院系表';

-- ----------------------------
-- Table structure for t_patrol_pre_plan
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_pre_plan`;
CREATE TABLE `t_patrol_pre_plan` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `pre_plan_name` varchar(100) NOT NULL COMMENT '预案名称',
  `pre_plan_type` tinyint(4) DEFAULT NULL COMMENT '预案类型 1-教室 2-科目',
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
  KEY `idx_create_user_id` (`create_user_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课-预案表';

-- ----------------------------
-- Table structure for t_patrol_pre_plan_range
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_pre_plan_range`;
CREATE TABLE `t_patrol_pre_plan_range` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `pre_plan_id` bigint(20) DEFAULT NULL COMMENT '预案id',
  `refer_id` bigint(20) DEFAULT NULL COMMENT '关联id,教室或科目id',
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
  KEY `idx_pre_plan_id` (`pre_plan_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课-预案范围表';

-- ----------------------------
-- Table structure for t_patrol_sensitive_words
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_sensitive_words`;
CREATE TABLE `t_patrol_sensitive_words` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `sensitive_word_name` varchar(50) NOT NULL COMMENT '敏感词名称',
  `sensitive_word_code` varchar(50) NOT NULL COMMENT '敏感词编码',
  `lexicon_id` bigint(20) NOT NULL COMMENT '词库ID',
  `level` smallint(6) DEFAULT NULL COMMENT '危险级别 1低危 2中危 3高危',
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
  KEY `idx_tenant_id` (`tenant_id`) USING BTREE,
  KEY `idx_sensitive_word_name` (`sensitive_word_name`) USING BTREE,
  KEY `idx_lexicon_id` (`lexicon_id`) USING BTREE,
  KEY `idx_level` (`level`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2039168677740392451 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='敏感词';

-- ----------------------------
-- Table structure for t_patrol_subject_org_rel
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_subject_org_rel`;
CREATE TABLE `t_patrol_subject_org_rel` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键id',
  `subject_white_id` bigint(20) NOT NULL COMMENT '科目白名单id',
  `org_id` bigint(20) NOT NULL COMMENT '组织id',
  `org_code` varchar(64) NOT NULL COMMENT '院系编码',
  `org_name` varchar(64) DEFAULT NULL COMMENT '院系名称',
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
  KEY `idx_subject_white_id` (`subject_white_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2019695314501271556 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='敏感词类别科目白名单关联开课院系';

-- ----------------------------
-- Table structure for t_patrol_subject_white
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_subject_white`;
CREATE TABLE `t_patrol_subject_white` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `subject_name` varchar(50) NOT NULL COMMENT '科目名称',
  `subject_code` varchar(50) NOT NULL COMMENT '科目编码',
  `lexicon_id` bigint(20) NOT NULL COMMENT '词库ID',
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
  KEY `idx_tenant_id` (`tenant_id`) USING BTREE,
  KEY `idx_lexicon_id` (`lexicon_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2019695314450939907 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='敏感词-科目白名单';

-- ----------------------------
-- Table structure for t_patrol_teacher_face_info
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_teacher_face_info`;
CREATE TABLE `t_patrol_teacher_face_info` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `user_code` varchar(50) NOT NULL COMMENT '用户code',
  `user_name` varchar(50) NOT NULL COMMENT '用户姓名',
  `face_image_path` varchar(500) DEFAULT NULL COMMENT '人脸图片相对路径',
  `face_image_id` bigint(20) DEFAULT NULL COMMENT '人脸图片id',
  `face_image_resolution` varchar(50) DEFAULT NULL COMMENT '人脸图片分辨率',
  `face_image_quality` varchar(255) DEFAULT NULL COMMENT '人脸图片质量',
  `upload_status` tinyint(4) DEFAULT NULL COMMENT '上传状态（0-失败，1-成功）',
  `upload_msg` varchar(255) DEFAULT NULL COMMENT '上传失败消息',
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
  KEY `idx_name` (`user_code`) USING BTREE,
  KEY `idx_code` (`user_name`) USING BTREE,
  KEY `idx_tenant_org_code` (`tenant_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2043511800186155010 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='教师人脸信息表';

-- ----------------------------
-- Table structure for t_patrol_teacher_org_rel
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_teacher_org_rel`;
CREATE TABLE `t_patrol_teacher_org_rel` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键id',
  `user_id` bigint(20) NOT NULL COMMENT '用户id',
  `org_id` bigint(20) NOT NULL COMMENT '组织id',
  `org_code` varchar(64) NOT NULL COMMENT '院系编码',
  `org_name` varchar(64) DEFAULT NULL COMMENT '院系名称',
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
  KEY `idx_user_id` (`user_id`) USING BTREE,
  KEY `idx_org_code` (`org_code`) USING BTREE,
  KEY `idx_org_name` (`org_name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2043512416757231618 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='教师人脸关联开课院系';

-- ----------------------------
-- Table structure for t_patrol_user_ignore_record
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_user_ignore_record`;
CREATE TABLE `t_patrol_user_ignore_record` (
  `id` bigint(20) NOT NULL COMMENT '主键',
  `record_type` tinyint(4) DEFAULT NULL COMMENT '预警类型 1-学情 2-教情 3-设备 4-空间',
  `record_id` bigint(20) DEFAULT NULL COMMENT '关联的预警记录id',
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
  KEY `idx_create_user_id` (`create_user_id`) USING BTREE,
  KEY `idx_record_id` (`record_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课-用户忽略预警弹框记录';

-- ----------------------------
-- Table structure for t_patrol_user_setting
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_user_setting`;
CREATE TABLE `t_patrol_user_setting` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `user_id` bigint(20) DEFAULT NULL COMMENT '用户id',
  `settings_json` json DEFAULT NULL COMMENT '设置json 例如预警方式等',
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
  KEY `idx_user_id` (`user_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课-用户AI巡课设置表';

-- ----------------------------
-- Table structure for t_patrol_user_tip_config
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_user_tip_config`;
CREATE TABLE `t_patrol_user_tip_config` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `user_id` bigint(20) DEFAULT NULL COMMENT '用户id',
  `tip_type` smallint(6) NOT NULL COMMENT '提示类型 1:视窗数量过多',
  `show_flag` tinyint(1) DEFAULT NULL COMMENT '是否显示 0-否 1-是',
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
  KEY `idx_user_id` (`user_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='AI巡课-用户提示-配置表';

-- ----------------------------
-- Table structure for t_patrol_warning_level
-- ----------------------------
DROP TABLE IF EXISTS `t_patrol_warning_level`;
CREATE TABLE `t_patrol_warning_level` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  `warning_level_code` varchar(100) DEFAULT NULL COMMENT '预警等级code',
  `alarm_level` smallint(6) DEFAULT NULL COMMENT '提醒等级 1 高  2 中  3 低 4 提示',
  `event_source_id` bigint(20) DEFAULT NULL COMMENT '事件类型id',
  `event_type` smallint(6) DEFAULT NULL COMMENT '事件类型 1学情 2教情 3 设备 4 空间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_event_source_id` (`event_source_id`) USING BTREE,
  KEY `idx_tenant_org_code` (`tenant_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2039221060017172482 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='预警等级表';

-- ----------------------------
-- Table structure for t_role_bind_own_org
-- ----------------------------
DROP TABLE IF EXISTS `t_role_bind_own_org`;
CREATE TABLE `t_role_bind_own_org` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键id',
  `role_id` bigint(20) NOT NULL COMMENT '角色ID',
  `role_code` varchar(255) NOT NULL COMMENT '角色标识',
  `bind_own_org_enable` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否绑定所属院系（0：否，1：是）',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(255) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(255) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_role_id` (`role_id`) USING BTREE,
  KEY `idx_tenant_id` (`tenant_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2042557142647058434 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='角色是否绑定所属院系';

-- ----------------------------
-- Table structure for t_role_classroom_permission
-- ----------------------------
DROP TABLE IF EXISTS `t_role_classroom_permission`;
CREATE TABLE `t_role_classroom_permission` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键id',
  `role_id` bigint(20) NOT NULL COMMENT '角色ID',
  `role_code` varchar(255) NOT NULL COMMENT '角色标识',
  `clro_id` bigint(20) NOT NULL COMMENT '教室ID',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(255) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(255) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_role_id` (`role_id`) USING BTREE,
  KEY `idx_classroom_id` (`clro_id`) USING BTREE,
  KEY `idx_tenant_id` (`tenant_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2019664323129516035 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='角色教室绑定关系表';

-- ----------------------------
-- Table structure for t_role_organization_permission
-- ----------------------------
DROP TABLE IF EXISTS `t_role_organization_permission`;
CREATE TABLE `t_role_organization_permission` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键id',
  `role_id` bigint(20) NOT NULL COMMENT '角色ID',
  `role_code` varchar(255) NOT NULL COMMENT '角色标识',
  `org_id` bigint(20) NOT NULL COMMENT '院系ID',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(255) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(255) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_role_id` (`role_id`) USING BTREE,
  KEY `idx_org_id` (`org_id`) USING BTREE,
  KEY `idx_tenant_id` (`tenant_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2042557142613504003 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='角色院系绑定关系表';

-- ----------------------------
-- Table structure for t_space_overview
-- ----------------------------
DROP TABLE IF EXISTS `t_space_overview`;
CREATE TABLE `t_space_overview` (
  `id` bigint(20) NOT NULL COMMENT ' 主键ID（雪花算法生成）',
  `classroom_id` bigint(20) DEFAULT NULL COMMENT '教室id',
  `classroom_code` varchar(255) DEFAULT NULL COMMENT '教室编号',
  `classroom_name` varchar(255) DEFAULT NULL COMMENT '教室名称',
  `camp_id` bigint(20) DEFAULT NULL COMMENT '校区id',
  `build_id` bigint(20) DEFAULT NULL COMMENT '教学楼id',
  `detection_date` datetime DEFAULT NULL COMMENT '检测日期',
  `space_seat_num` int(11) DEFAULT NULL COMMENT '教室座位数',
  `space_usage_percent` decimal(20,2) DEFAULT NULL COMMENT '检查日期空间使用率',
  `space_utilization_percent` decimal(20,2) DEFAULT NULL COMMENT '检查日期空间利用率',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT ' 最后修改时间 ',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT ' 租户编号 ',
  `floor_num` int(11) DEFAULT NULL COMMENT '教室楼层数',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_classroom_id` (`classroom_id`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_detection_date` (`detection_date`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_detection_date_classroom_id` (`detection_date`,`classroom_id`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_camp_id` (`camp_id`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_space_usage_percent` (`space_usage_percent`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_space_utilization_percent` (`space_utilization_percent`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_build_id` (`build_id`,`delete_flag`,`tenant_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='空间概览表';

-- ----------------------------
-- Table structure for t_space_overview_detail
-- ----------------------------
DROP TABLE IF EXISTS `t_space_overview_detail`;
CREATE TABLE `t_space_overview_detail` (
  `id` bigint(20) NOT NULL COMMENT ' 主键ID（雪花算法生成）',
  `space_id` bigint(20) DEFAULT NULL COMMENT '空间概览表主键id',
  `detection_date` datetime DEFAULT NULL COMMENT '检测日期',
  `classroom_id` bigint(20) DEFAULT NULL COMMENT '教室id',
  `leti_number` smallint(6) NOT NULL COMMENT '节次',
  `space_status` smallint(6) NOT NULL COMMENT '空间状态 1：有课 2：无课 3：自习 4：借用',
  `abnormal_count` int(11) DEFAULT '0' COMMENT '异常课次数量',
  `space_seat_percent` decimal(20,2) DEFAULT NULL COMMENT '空间就座率',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT ' 最后修改时间 ',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  `normal_count` int(11) DEFAULT NULL COMMENT '节次课程总数量',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_space_id` (`space_id`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_space_id_status` (`space_id`,`space_status`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='空间概览详情表';

-- ----------------------------
-- Table structure for t_tias_acte_avg_static
-- ----------------------------
DROP TABLE IF EXISTS `t_tias_acte_avg_static`;
CREATE TABLE `t_tias_acte_avg_static` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成',
  `acte_id` bigint(20) DEFAULT NULL COMMENT '学年学期id',
  `tias_att_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias出勤率',
  `tias_rise_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias抬头率',
  `tias_late_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias迟到率',
  `tias_front_row_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias前排就座率',
  `tias_front_full_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias前排满座率',
  `tias_concentration` decimal(20,2) DEFAULT NULL COMMENT '专注度节次平均值',
  `tias_seat_use_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias教室座位利用率',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT ' 创建人id ',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT ' 更新人id ',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT ' 乐观锁版本号 ',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT ' 创建时间 ',
  `created_by` varchar(50) DEFAULT NULL COMMENT ' 创建人 ',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT ' 最后修改时间 ',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT ' 最后修改人 ',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT ' 删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT ' 租户编号 ',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_acte_id` (`acte_id`) USING BTREE,
  KEY `idx_acte_id_tenant_id` (`acte_id`,`tenant_id`,`delete_flag`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='学期全校课程的三率相关信息的平均值';

-- ----------------------------
-- Table structure for t_tias_classroom
-- ----------------------------
DROP TABLE IF EXISTS `t_tias_classroom`;
CREATE TABLE `t_tias_classroom` (
  `id` bigint(20) NOT NULL COMMENT ' 主键ID（雪花算法生成）',
  `classroom_id` bigint(20) DEFAULT NULL COMMENT ' 教室id ',
  `classroom_code` varchar(255) DEFAULT NULL COMMENT '教室编号',
  `classroom_name` varchar(255) DEFAULT NULL COMMENT '教室名称',
  `begin_time` datetime DEFAULT NULL COMMENT '开始时间',
  `end_time` datetime DEFAULT NULL COMMENT '结束时间',
  `tias_seat_num` int(11) DEFAULT NULL COMMENT 'tias座位数',
  `tias_front_seat_num` int(11) DEFAULT NULL COMMENT 'tias前排座位数',
  `tias_people_num` int(11) DEFAULT NULL COMMENT 'tias就坐人数',
  `tias_seat_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias就座率',
  `tias_free_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias空闲率',
  `has_course` smallint(6) DEFAULT NULL COMMENT '是否有课 0 无课 1有课',
  `has_people` smallint(6) DEFAULT NULL COMMENT '是否有人 0 无人 1有人',
  `has_image` smallint(6) DEFAULT NULL COMMENT '是否有图片 0 无 1有',
  `has_video` smallint(6) DEFAULT NULL COMMENT '是否有视频 0 无 1有',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT ' 创建人id ',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT ' 更新人id ',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT ' 乐观锁版本号 ',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT ' 创建时间 ',
  `created_by` varchar(50) DEFAULT NULL COMMENT ' 创建人 ',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT ' 最后修改时间 ',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT ' 最后修改人 ',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT ' 删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT ' 租户编号 ',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_classroom_id` (`classroom_id`) USING BTREE,
  KEY `idx_begin_time` (`begin_time`) USING BTREE,
  KEY `idx_end_time` (`end_time`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_begin_time_end_time` (`begin_time`,`end_time`) USING BTREE,
  KEY `idx_begin_time_end_time_classroom_id` (`begin_time`,`end_time`,`classroom_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='教室tias数据';

-- ----------------------------
-- Table structure for t_tias_classroom_detail
-- ----------------------------
DROP TABLE IF EXISTS `t_tias_classroom_detail`;
CREATE TABLE `t_tias_classroom_detail` (
  `id` bigint(20) NOT NULL COMMENT ' 主键ID（雪花算法生成）',
  `tc_id` bigint(20) DEFAULT NULL COMMENT ' tias教室表主键 ',
  `classroom_id` bigint(20) DEFAULT NULL COMMENT ' 教室id ',
  `classroom_code` varchar(255) DEFAULT NULL COMMENT '教室编号',
  `classroom_name` varchar(255) DEFAULT NULL COMMENT '教室名称',
  `tias_event_time` datetime DEFAULT NULL COMMENT ' tias事件时间 ',
  `tias_seat_num` int(11) DEFAULT NULL COMMENT ' tias座位数 ',
  `tias_front_seat_num` int(11) DEFAULT NULL COMMENT 'tias前排座位数',
  `tias_people_num` int(11) DEFAULT NULL COMMENT ' tias就坐人数 ',
  `tias_seat_percent` decimal(20,2) DEFAULT NULL COMMENT ' tias就座率 ',
  `tias_free_percent` decimal(20,2) DEFAULT NULL COMMENT ' tias空闲率 ',
  `tias_image_urls` text COMMENT ' tias图片地址列表 ',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT ' 创建人id ',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT ' 更新人id ',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT ' 乐观锁版本号 ',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT ' 创建时间 ',
  `created_by` varchar(50) DEFAULT NULL COMMENT ' 创建人 ',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT ' 最后修改时间 ',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT ' 最后修改人 ',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT ' 删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT ' 租户编号 ',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_tc_id` (`tc_id`) USING BTREE,
  KEY `idx_tias_event_time` (`tias_event_time`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_classroom_id` (`classroom_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='教室tias数据详情表';

-- ----------------------------
-- Table structure for t_tias_course
-- ----------------------------
DROP TABLE IF EXISTS `t_tias_course`;
CREATE TABLE `t_tias_course` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `course_id` bigint(20) DEFAULT NULL COMMENT '课程id',
  `subject_id` bigint(20) DEFAULT NULL COMMENT '科目id',
  `subject_code` varchar(255) DEFAULT NULL COMMENT '科目编码',
  `subject_name` varchar(255) DEFAULT NULL COMMENT '科目名称',
  `tecl_org_id` bigint(20) DEFAULT NULL COMMENT '开课学院id',
  `tecl_org_code` varchar(255) DEFAULT NULL COMMENT '开课学院编码',
  `tias_teacher_late_status` smallint(6) DEFAULT NULL COMMENT '教师是否迟到 0-否 1是',
  `tecl_org_name` varchar(255) DEFAULT NULL COMMENT '开课学院名称',
  `subject_source` smallint(6) DEFAULT NULL COMMENT '科目来源 1 本科生 2 研究生',
  `teaching_class_id` bigint(20) DEFAULT NULL COMMENT '教学班id',
  `teaching_class_code` varchar(600) DEFAULT NULL COMMENT '教学班编号',
  `teaching_class_name` varchar(600) DEFAULT NULL COMMENT '教学班名称',
  `course_start_time` datetime DEFAULT NULL COMMENT '课程开始时间',
  `course_end_time` datetime DEFAULT NULL COMMENT '课程结束时间',
  `classroom_id` bigint(20) DEFAULT NULL COMMENT '教室id',
  `classroom_code` varchar(255) DEFAULT NULL COMMENT '教室编码',
  `classroom_name` varchar(255) DEFAULT NULL COMMENT '教室名称',
  `teacher_codes` varchar(255) DEFAULT NULL COMMENT '上课老师编码列表',
  `teacher_names` varchar(255) DEFAULT NULL COMMENT '上课老师姓名列表',
  `acte_id` bigint(20) DEFAULT NULL COMMENT '学期学年id',
  `leti_number` bigint(20) DEFAULT NULL COMMENT '课程节次',
  `leti_name` varchar(255) DEFAULT NULL COMMENT '节次名称',
  `tias_event_time` datetime DEFAULT NULL COMMENT 'tias事件时间',
  `tias_teacher_event_time` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT 'tias教师事件时间',
  `tias_need_att_num` int(11) DEFAULT NULL COMMENT 'tias应到学生数',
  `tias_actual_att_num` int(11) DEFAULT NULL COMMENT 'tias实到学生数',
  `tias_front_row_num` int(11) DEFAULT NULL COMMENT 'tias前排就座人数',
  `tias_middle_row_num` int(11) DEFAULT NULL COMMENT 'tias中排人数',
  `tias_back_row_num` int(11) DEFAULT NULL COMMENT 'tias后排人数',
  `tias_late_num` int(11) DEFAULT NULL COMMENT 'tias迟到学生数',
  `tias_teacher_count` int(11) DEFAULT NULL COMMENT '教师到勤人数',
  `tias_on_time_att_num` int(11) DEFAULT NULL COMMENT '学生准点人数',
  `tias_seat_num` int(11) DEFAULT NULL COMMENT 'tias座位数',
  `tias_rise_num` int(11) DEFAULT NULL COMMENT 'tias抬头人数',
  `tias_avg_reading_num` decimal(20,2) DEFAULT NULL COMMENT '阅读人数（平均值）',
  `tias_avg_phone_use_num` decimal(20,2) DEFAULT NULL COMMENT '使用手机人数（平均值）',
  `tias_avg_rise_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias平均抬头率',
  `tias_avg_sleep_num` decimal(20,2) DEFAULT NULL COMMENT '趴桌/睡觉人数节次平均值',
  `tias_avg_concentration` decimal(20,2) DEFAULT NULL COMMENT '专注度节次平均值',
  `tias_teacher_early_status` smallint(6) DEFAULT NULL COMMENT '教师早退状态 0准时 1早退',
  `tias_att_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias到勤率',
  `tias_front_row_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias前排就座率',
  `tias_rise_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias抬头率',
  `tias_front_full_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias前排满座率',
  `tias_seat_use_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias教室座位利用率',
  `tias_late_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias迟到率',
  `tias_seating_ratio` decimal(20,2) DEFAULT NULL COMMENT 'tias前后排就座比',
  `tias_att_percent_chart` text COMMENT 'tias到勤率图表',
  `tias_rise_percent_chart` text COMMENT 'tias抬头率图表',
  `has_image` smallint(6) DEFAULT NULL COMMENT '是否有图片 0 无 1有',
  `has_video` smallint(6) DEFAULT NULL COMMENT '是否有视频 0 无 1有',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  `has_people` smallint(6) DEFAULT '1' COMMENT '疑似无人 1-有人 0-无人',
  `attendance_waring` smallint(6) DEFAULT '0' COMMENT '出勤率告警 0-无 1-有',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_tenant_id` (`tenant_id`) USING BTREE,
  KEY `idx_course_id` (`course_id`) USING BTREE,
  KEY `idx_subject_id` (`subject_id`) USING BTREE,
  KEY `idx_teaching_class_id` (`teaching_class_id`) USING BTREE,
  KEY `idx_classroom_id` (`classroom_id`) USING BTREE,
  KEY `idx_insert_time` (`created_date_time`) USING BTREE,
  KEY `idx_subject_source` (`subject_source`) USING BTREE,
  KEY `idx_course_start_time` (`course_start_time`) USING BTREE,
  KEY `idx_course_end_time` (`course_end_time`) USING BTREE,
  KEY `course_start_time_end_time` (`course_start_time`,`course_end_time`) USING BTREE,
  KEY `idx_tias_att_percent` (`tias_att_percent`) USING BTREE,
  KEY `idx_tias_front_row_percent` (`tias_front_row_percent`) USING BTREE,
  KEY `idx_tias_rise_percent` (`tias_rise_percent`) USING BTREE,
  KEY `idx_tias_front_full_percent` (`tias_front_full_percent`) USING BTREE,
  KEY `idx_tias_seat_use_percent` (`tias_seat_use_percent`) USING BTREE,
  KEY `idx_tias_late_percent` (`tias_late_percent`) USING BTREE,
  KEY `idx_course_id_tias_event_time` (`course_id`,`tias_event_time`) USING BTREE,
  KEY `idx_update_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_delete_event_time` (`delete_flag`,`tias_event_time`) USING BTREE,
  KEY `idx_classroom_delete_time` (`classroom_id`,`delete_flag`,`course_start_time`) USING BTREE,
  FULLTEXT KEY `idx_ft_subject` (`subject_code`,`subject_name`),
  FULLTEXT KEY `idx_ft_teachingclass` (`teaching_class_code`,`teaching_class_name`),
  FULLTEXT KEY `idx_ft_teacher` (`teacher_codes`,`teacher_names`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='tias数据表-课程维度';

-- ----------------------------
-- Table structure for t_tias_course_student_detail
-- ----------------------------
DROP TABLE IF EXISTS `t_tias_course_student_detail`;
CREATE TABLE `t_tias_course_student_detail` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `course_id` bigint(20) DEFAULT NULL COMMENT '课程id',
  `tias_event_time` datetime DEFAULT NULL COMMENT 'tias事件时间',
  `tias_need_att_num` int(11) DEFAULT NULL COMMENT 'tias应到学生数',
  `tias_actual_att_num` int(11) DEFAULT NULL COMMENT 'tias实到学生数',
  `tias_front_row_num` int(11) DEFAULT NULL COMMENT 'tias前排就座人数',
  `tias_middle_row_num` int(11) DEFAULT NULL COMMENT 'tias中排人数',
  `tias_back_row_num` int(11) DEFAULT NULL COMMENT 'tias后排人数',
  `tias_late_num` int(11) DEFAULT NULL COMMENT 'tias迟到学生数',
  `tias_teacher_count` int(11) DEFAULT NULL COMMENT '教师到勤人数',
  `tias_on_time_att_num` int(11) DEFAULT NULL COMMENT '学生准点人数',
  `tias_seat_num` int(11) DEFAULT NULL COMMENT 'tias座位数',
  `tias_rise_num` int(11) DEFAULT NULL COMMENT 'tias抬头人数',
  `tias_att_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias到勤率',
  `tias_front_row_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias前排就座率',
  `tias_rise_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias抬头率',
  `tias_front_full_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias前排满座率',
  `tias_seat_use_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias教室座位利用率',
  `tias_late_percent` decimal(20,2) DEFAULT NULL COMMENT 'tias迟到率',
  `tias_seating_ratio` decimal(20,2) DEFAULT NULL COMMENT 'tias前后排就座比',
  `tias_reading_num` decimal(20,2) DEFAULT NULL COMMENT '阅读人数',
  `tias_phone_use_num` decimal(20,2) DEFAULT NULL COMMENT '使用手机人数',
  `tias_sleep_num` decimal(20,2) DEFAULT NULL COMMENT '趴桌/睡觉人数',
  `tias_concentration` decimal(20,2) DEFAULT NULL COMMENT '专注度',
  `tias_image_urls` text COMMENT 'tias图片地址列表',
  `tias_image_ids` text COMMENT 'tias图片id列表',
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
  KEY `idx_course_id` (`course_id`) USING BTREE,
  KEY `inx_tias_event_time` (`tias_event_time`) USING BTREE,
  KEY `idx_update_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_delete_flag` (`delete_flag`) USING BTREE,
  KEY `idx_course_id_event_time` (`course_id`,`tias_event_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='tias数据明细表-学生课程维度';

-- ----------------------------
-- Table structure for t_tias_course_teacher_detail
-- ----------------------------
DROP TABLE IF EXISTS `t_tias_course_teacher_detail`;
CREATE TABLE `t_tias_course_teacher_detail` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `course_id` bigint(20) DEFAULT NULL COMMENT '课程id',
  `tias_event_time` datetime DEFAULT NULL COMMENT 'tias事件时间',
  `tias_teacher_count` int(11) DEFAULT NULL COMMENT 'tias实到老师数',
  `tias_teacher_late_status` smallint(6) DEFAULT NULL COMMENT '教师迟到状态 0准时 1迟到',
  `tias_teacher_early_status` smallint(6) DEFAULT NULL COMMENT '教师早退状态 0准时 1早退',
  `tias_image_urls` text COMMENT 'tias图片地址列表',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `ai_teacher_name` varchar(255) DEFAULT NULL COMMENT 'ai分析返回的教师姓名',
  `ai_teacher_code` varchar(255) DEFAULT NULL COMMENT 'ai分析返回的教师编码',
  `tenant_id` varchar(255) DEFAULT NULL COMMENT '租户标识',
  `tias_image_ids` varchar(255) DEFAULT NULL COMMENT '图片id',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_course_id` (`course_id`) USING BTREE,
  KEY `inx_tias_event_time` (`tias_event_time`) USING BTREE,
  KEY `idx_update_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_delete_flag` (`delete_flag`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='tias数据明细表-教师课程维度';

-- ----------------------------
-- Table structure for t_tias_course_waring_type
-- ----------------------------
DROP TABLE IF EXISTS `t_tias_course_waring_type`;
CREATE TABLE `t_tias_course_waring_type` (
  `id` bigint(20) NOT NULL COMMENT ' 主键ID（雪花算法生成）',
  `course_id` bigint(20) DEFAULT NULL COMMENT ' tias教室表主键 ',
  `waring_type_code` varchar(50) NOT NULL COMMENT ' 课程预警类型',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT ' 创建人id ',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT ' 更新人id ',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT ' 乐观锁版本号 ',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT ' 创建时间 ',
  `created_by` varchar(50) DEFAULT NULL COMMENT ' 创建人 ',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT ' 最后修改时间 ',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT ' 最后修改人 ',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT ' 删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT ' 租户编号 ',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_course_id` (`course_id`) USING BTREE,
  KEY `idx_course_id_alarm_type` (`course_id`,`waring_type_code`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_course_waring` (`course_id`,`waring_type_code`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='tias课程预警类型关系表';

-- ----------------------------
-- Table structure for t_video_record_plan
-- ----------------------------
DROP TABLE IF EXISTS `t_video_record_plan`;
CREATE TABLE `t_video_record_plan` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `plan_id` varchar(255) DEFAULT NULL COMMENT '媒体录像计划id',
  `record_plan_name` varchar(255) DEFAULT NULL COMMENT '计划录像名称',
  `camp_id` bigint(20) NOT NULL COMMENT '校区id',
  `record_cycles` text NOT NULL COMMENT '计划录像周期',
  `switch_file` tinyint(4) DEFAULT NULL COMMENT '是否切片',
  `record_plan_status` tinyint(4) DEFAULT NULL COMMENT '录像计划状态 1:正常 0:禁用',
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
  KEY `idx_video_plan_key` (`plan_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='录像计划表';

-- ----------------------------
-- Table structure for t_voice_analysis_history
-- ----------------------------
DROP TABLE IF EXISTS `t_voice_analysis_history`;
CREATE TABLE `t_voice_analysis_history` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  `task_id` varchar(64) DEFAULT NULL COMMENT '任务ID',
  `start_time` datetime DEFAULT NULL COMMENT '分析开始时间',
  `end_time` datetime DEFAULT NULL COMMENT '分析结束时间',
  `start_time_second` double DEFAULT NULL COMMENT '音频段起始时间（秒）',
  `end_time_second` double DEFAULT NULL COMMENT '音频段结束时间（秒）',
  `volume_db` int(11) DEFAULT NULL COMMENT '音量分贝值',
  `error_msg` varchar(2000) DEFAULT NULL COMMENT '错误信息',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_task_id` (`task_id`) USING BTREE,
  KEY `idx_start_time` (`start_time`) USING BTREE,
  KEY `idx_tenant_id` (`tenant_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2038569424289329155 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='声音检测历史记录表';

-- ----------------------------
-- Table structure for t_voice_analysis_task
-- ----------------------------
DROP TABLE IF EXISTS `t_voice_analysis_task`;
CREATE TABLE `t_voice_analysis_task` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  `cour_id` bigint(20) DEFAULT NULL COMMENT '课程ID',
  `task_id` varchar(64) DEFAULT NULL COMMENT '任务ID',
  `stream_type` varchar(32) DEFAULT NULL COMMENT '流类型',
  `status` int(11) DEFAULT NULL COMMENT '任务状态: 0-创建失败 1-创建成功 2-正在分析',
  `course_start_time` datetime DEFAULT NULL COMMENT '课程开始时间',
  `course_end_time` datetime DEFAULT NULL COMMENT '课程结束时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_task_id` (`task_id`) USING BTREE,
  KEY `idx_cour_id` (`cour_id`) USING BTREE,
  KEY `idx_tenant_id` (`tenant_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2038549736276684803 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='音频分析任务表';

-- ----------------------------
-- Table structure for t_warning_course_teacher
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_course_teacher`;
CREATE TABLE `t_warning_course_teacher` (
  `id` bigint(20) NOT NULL COMMENT '主键ID',
  `course_id` bigint(20) NOT NULL COMMENT '课程id',
  `teacher_user_id` bigint(20) NOT NULL COMMENT '授课老师id',
  `teacher_user_code` varchar(255) DEFAULT NULL COMMENT '授课老师编号',
  `teacher_user_name` varchar(255) DEFAULT NULL COMMENT '授课老师名称',
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
  UNIQUE KEY `idx_course_teacher_id` (`course_id`,`teacher_user_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='预警-课程授课老师表';

-- ----------------------------
-- Table structure for t_warning_device_check_item
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_device_check_item`;
CREATE TABLE `t_warning_device_check_item` (
  `id` bigint(20) NOT NULL COMMENT '主键ID',
  `device_record_id` bigint(20) NOT NULL COMMENT '设备预警表id',
  `channel_gb_id` varchar(255) NOT NULL COMMENT '设备通道国标id',
  `channel_name` varchar(255) DEFAULT NULL COMMENT '设备通道名称',
  `view_num` tinyint(4) DEFAULT NULL COMMENT '视角；1-教师1，2-教师2，3-学生1，4-学生2，5-PPT，6-电子白板，7-合成通道',
  `view_name` varchar(255) DEFAULT NULL COMMENT '视角名称；例如：教师1，教师2，学生1，学生2，PPT，电子白板，合成通道',
  `abnormal_type` tinyint(2) DEFAULT NULL COMMENT '异常类型',
  `abnormal_name` varchar(255) DEFAULT NULL COMMENT '异常名称',
  `check_type` tinyint(2) DEFAULT NULL COMMENT '检查类型；1-设备离线，2-视频质量诊断',
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
  KEY `idx_device_record_id` (`device_record_id`) USING BTREE,
  KEY `idx_channel_gb_id` (`channel_gb_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='预警-设备检查项';

-- ----------------------------
-- Table structure for t_warning_device_record
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_device_record`;
CREATE TABLE `t_warning_device_record` (
  `id` bigint(20) NOT NULL COMMENT '主键ID',
  `strategy_id` bigint(20) NOT NULL COMMENT '策略id',
  `indicator_id` bigint(20) NOT NULL COMMENT '预警指标id',
  `indicator_code` varchar(100) DEFAULT NULL COMMENT '预警指标code',
  `indicator_name` varchar(100) DEFAULT NULL COMMENT '预警指标名称',
  `warning_content` varchar(1000) DEFAULT NULL COMMENT '预警内容',
  `warning_level` tinyint(4) DEFAULT NULL COMMENT '预警等级；1-高  2-中  3-低 4-提示',
  `warning_time` datetime DEFAULT NULL COMMENT '预警时间',
  `acte_id` bigint(20) DEFAULT NULL COMMENT '学年学期id',
  `course_id` bigint(20) DEFAULT NULL COMMENT '课程id',
  `have_class` tinyint(4) DEFAULT NULL COMMENT '是否有课；1-有 2-无',
  `subject_id` bigint(20) DEFAULT NULL COMMENT '科目id',
  `subject_code` varchar(255) DEFAULT NULL COMMENT '科目编号',
  `subject_name` varchar(255) DEFAULT NULL COMMENT '科目名称',
  `channel_gb_id` varchar(255) DEFAULT NULL COMMENT '设备通道国标id',
  `view_name` varchar(255) DEFAULT NULL COMMENT '视角名称，多个用逗号隔开；例如：教师1，教师2，学生1，学生2，PPT，电子白板，合成通道',
  `clro_id` bigint(20) DEFAULT NULL COMMENT '教室id',
  `clro_code` varchar(255) DEFAULT NULL COMMENT '教室编号',
  `clro_name` varchar(255) DEFAULT NULL COMMENT '教室名称',
  `build_id` bigint(20) DEFAULT NULL COMMENT '教学楼id',
  `build_name` varchar(255) DEFAULT NULL COMMENT '教学楼名称',
  `campus_id` bigint(20) DEFAULT NULL COMMENT '校区id',
  `campus_name` varchar(255) DEFAULT NULL COMMENT '校区名称',
  `org_id` bigint(20) DEFAULT NULL COMMENT '开课院系id',
  `org_code` varchar(255) DEFAULT NULL COMMENT '开课院系编号',
  `org_name` varchar(255) DEFAULT NULL COMMENT '开课院系名称',
  `handle_status` tinyint(4) DEFAULT NULL COMMENT '处理状态；1-待处理 2-挂起 3-无异常 4-确认异常 5-已恢复',
  `recovery_time` datetime DEFAULT NULL COMMENT '恢复时间',
  `handle_user_id` bigint(20) DEFAULT NULL COMMENT '处理人id',
  `handle_user_code` varchar(255) DEFAULT NULL COMMENT '处理人编号',
  `handle_user_name` varchar(255) DEFAULT NULL COMMENT '处理人名称',
  `feedback_user_id` bigint(20) DEFAULT NULL COMMENT '反馈人id',
  `feedback_user_code` varchar(255) DEFAULT NULL COMMENT '反馈人编号',
  `feedback_user_name` varchar(255) DEFAULT NULL COMMENT '反馈人名称',
  `feedback_type` tinyint(4) DEFAULT NULL COMMENT '反馈类型；1-不反馈 2-反馈给院系联络人 3-反馈给指定人员',
  `feedback_status` tinyint(4) DEFAULT NULL COMMENT '反馈状态；1-未反馈 2-成功 3-失败 4-无需反馈',
  `handle_description` varchar(512) DEFAULT NULL COMMENT '处理说明',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  `warning_time_day` date GENERATED ALWAYS AS (cast(`warning_time` as date)) STORED COMMENT '预警日期（由 warning_time 计算得出）',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_warning_time` (`warning_time`) USING BTREE,
  KEY `idx_indicator_id` (`indicator_id`) USING BTREE,
  KEY `idx_clro_id` (`clro_id`) USING BTREE,
  KEY `idx_course_id` (`course_id`) USING BTREE,
  KEY `idx_org_id` (`org_id`) USING BTREE,
  KEY `idx_warning_level` (`warning_level`) USING BTREE,
  KEY `idx_channel_gb_id` (`channel_gb_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_warning_time_day` (`delete_flag`,`warning_time_day`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='预警-设备预警';

-- ----------------------------
-- Table structure for t_warning_device_record_image
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_device_record_image`;
CREATE TABLE `t_warning_device_record_image` (
  `id` bigint(20) NOT NULL COMMENT '主键ID',
  `device_record_id` bigint(20) NOT NULL COMMENT '设备预警表ID',
  `channel_gb_id` varchar(255) NOT NULL COMMENT '设备通道国标id',
  `image_id` bigint(20) DEFAULT NULL COMMENT '图片id',
  `image_url` varchar(255) NOT NULL COMMENT '图片路径',
  `capture_time` datetime NOT NULL COMMENT '抓图时间',
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
  KEY `idx_device_record_id` (`device_record_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_channel_gb_id` (`channel_gb_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='预警-设备记录图片表';

-- ----------------------------
-- Table structure for t_warning_device_silence
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_device_silence`;
CREATE TABLE `t_warning_device_silence` (
  `id` bigint(20) NOT NULL COMMENT '主键id',
  `clro_id` bigint(20) DEFAULT NULL COMMENT '教室id',
  `indicator_code` varchar(100) DEFAULT NULL COMMENT '预警指标code',
  `silence_end_time` datetime DEFAULT NULL COMMENT '静默结束时间',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`),
  KEY `idx_clro_id_indicator_code` (`clro_id`,`indicator_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预警-设备预警静默表';

-- ----------------------------
-- Table structure for t_warning_feedback_receiver_user
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_feedback_receiver_user`;
CREATE TABLE `t_warning_feedback_receiver_user` (
  `id` bigint(20) NOT NULL COMMENT '主键ID',
  `record_id` bigint(20) NOT NULL COMMENT '预警表ID，包括学情、教情、设备、空间等',
  `warning_message_type` varchar(255) DEFAULT NULL COMMENT '预警消息类型；study：学情，teaching：教情，device：设备，space：空间',
  `read_status` tinyint(2) DEFAULT NULL COMMENT '读取状态；0：未读，1：已读',
  `receiver_user_id` bigint(20) DEFAULT NULL COMMENT '接收人用户id',
  `receiver_user_code` varchar(255) DEFAULT NULL COMMENT '接收人用户编号',
  `receiver_user_name` varchar(255) DEFAULT NULL COMMENT '接收人用户名称',
  `batch_no` bigint(20) DEFAULT NULL COMMENT '批次号',
  `batch_time` datetime DEFAULT NULL COMMENT '批次时间',
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
  KEY `idx_record_id` (`record_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_receiver_user_batch_no` (`receiver_user_id`,`batch_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='预警-反馈-接收用户表';

-- ----------------------------
-- Table structure for t_warning_record_handle_log
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_record_handle_log`;
CREATE TABLE `t_warning_record_handle_log` (
  `id` bigint(20) NOT NULL COMMENT '主键ID',
  `record_id` bigint(20) NOT NULL COMMENT '预警表ID',
  `record_type` bigint(20) NOT NULL COMMENT '预警类型 1-学情 2-教情 3-设备 4-空间',
  `handle_user_id` bigint(20) DEFAULT NULL COMMENT '处理人id',
  `handle_user_code` varchar(255) DEFAULT NULL COMMENT '处理人编号',
  `handle_user_name` varchar(255) DEFAULT NULL COMMENT '处理人名称',
  `handle_status` tinyint(4) DEFAULT NULL COMMENT '处理状态；1-待处理 2-挂起 3-无异常 4-确认异常 5-已恢复',
  `handle_description` varchar(512) DEFAULT NULL COMMENT '处理说明',
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
  KEY `idx_record_type_id` (`record_type`,`record_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='预警-处理日志表';

-- ----------------------------
-- Table structure for t_warning_space_record
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_space_record`;
CREATE TABLE `t_warning_space_record` (
  `id` bigint(20) NOT NULL COMMENT '主键ID',
  `strategy_id` bigint(20) NOT NULL COMMENT '策略id',
  `indicator_id` bigint(20) NOT NULL COMMENT '预警指标id',
  `indicator_code` varchar(100) DEFAULT NULL COMMENT '预警指标code',
  `indicator_name` varchar(100) DEFAULT NULL COMMENT '预警指标名称',
  `warning_content` varchar(512) DEFAULT NULL COMMENT '预警内容',
  `warning_level` tinyint(4) DEFAULT NULL COMMENT '预警等级；1-高  2-中  3-低 4-提示',
  `warning_time` datetime DEFAULT NULL COMMENT '预警时间',
  `clro_id` bigint(20) DEFAULT NULL COMMENT '教室id',
  `clro_code` varchar(255) DEFAULT NULL COMMENT '教室编号',
  `clro_name` varchar(255) DEFAULT NULL COMMENT '教室名称',
  `build_id` bigint(20) DEFAULT NULL COMMENT '教学楼id',
  `build_name` varchar(255) DEFAULT NULL COMMENT '教学楼名称',
  `campus_id` bigint(20) DEFAULT NULL COMMENT '校区id',
  `campus_name` varchar(255) DEFAULT NULL COMMENT '校区名称',
  `handle_status` tinyint(4) DEFAULT NULL COMMENT '处理状态；1-待处理 2-挂起 3-无异常 4-确认异常',
  `handle_user_id` bigint(20) DEFAULT NULL COMMENT '处理人id',
  `handle_user_code` varchar(255) DEFAULT NULL COMMENT '处理人编号',
  `handle_user_name` varchar(255) DEFAULT NULL COMMENT '处理人名称',
  `feedback_user_id` bigint(20) DEFAULT NULL COMMENT '反馈人id',
  `feedback_user_code` varchar(255) DEFAULT NULL COMMENT '反馈人编号',
  `feedback_user_name` varchar(255) DEFAULT NULL COMMENT '反馈人名称',
  `feedback_type` tinyint(4) DEFAULT NULL COMMENT '反馈类型；1-不反馈 2-反馈给院系联络人 3-反馈给指定人员',
  `feedback_status` tinyint(4) DEFAULT NULL COMMENT '反馈状态；1-未反馈 2-成功 3-失败 4-无需反馈',
  `handle_description` varchar(512) DEFAULT NULL COMMENT '处理说明',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  `warning_time_day` date GENERATED ALWAYS AS (cast(`warning_time` as date)) STORED COMMENT '预警日期（由 warning_time 计算得出）',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_warning_time` (`warning_time`) USING BTREE,
  KEY `idx_indicator_id` (`indicator_id`) USING BTREE,
  KEY `idx_clro_id` (`clro_id`) USING BTREE,
  KEY `idx_warning_level` (`warning_level`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_warning_time_day` (`delete_flag`,`warning_time_day`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='预警-空间预警';

-- ----------------------------
-- Table structure for t_warning_space_record_image
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_space_record_image`;
CREATE TABLE `t_warning_space_record_image` (
  `id` bigint(20) NOT NULL COMMENT '主键ID',
  `space_record_id` bigint(20) NOT NULL COMMENT '空间预警表ID',
  `channel_gb_id` varchar(255) NOT NULL COMMENT '设备通道国标id',
  `image_id` bigint(20) DEFAULT NULL COMMENT '图片id',
  `image_url` varchar(255) NOT NULL COMMENT '图片路径',
  `capture_time` datetime NOT NULL COMMENT '抓图时间',
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
  KEY `idx_space_record_id` (`space_record_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_channel_gb_id` (`channel_gb_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='预警-空间记录图片表';

-- ----------------------------
-- Table structure for t_warning_study_record
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_study_record`;
CREATE TABLE `t_warning_study_record` (
  `id` bigint(20) NOT NULL COMMENT '主键ID',
  `strategy_id` bigint(20) NOT NULL COMMENT '策略id',
  `indicator_id` bigint(20) NOT NULL COMMENT '预警指标id',
  `indicator_code` varchar(100) DEFAULT NULL COMMENT '预警指标code',
  `indicator_name` varchar(100) DEFAULT NULL COMMENT '预警指标名称',
  `warning_content` varchar(512) DEFAULT NULL COMMENT '预警内容',
  `warning_level` tinyint(4) DEFAULT NULL COMMENT '预警等级；1-高  2-中  3-低 4-提示',
  `warning_time` datetime DEFAULT NULL COMMENT '预警时间',
  `acte_id` bigint(20) DEFAULT NULL COMMENT '学年学期id',
  `course_id` bigint(20) DEFAULT NULL COMMENT '课程id',
  `course_name` varchar(255) DEFAULT NULL COMMENT '课程名称',
  `leti_number` bigint(20) DEFAULT NULL COMMENT '课程节次',
  `course_start_time` datetime DEFAULT NULL COMMENT '课程开始时间',
  `course_end_time` datetime DEFAULT NULL COMMENT '课程结束时间',
  `clro_id` bigint(20) DEFAULT NULL COMMENT '教室id',
  `clro_code` varchar(255) DEFAULT NULL COMMENT '教室编号',
  `clro_name` varchar(255) DEFAULT NULL COMMENT '教室名称',
  `subject_id` bigint(20) DEFAULT NULL COMMENT '科目id',
  `subject_code` varchar(255) DEFAULT NULL COMMENT '科目编号',
  `subject_name` varchar(255) DEFAULT NULL COMMENT '科目名称',
  `org_id` bigint(20) DEFAULT NULL COMMENT '开课院系id',
  `org_code` varchar(255) DEFAULT NULL COMMENT '开课院系编号',
  `org_name` varchar(255) DEFAULT NULL COMMENT '开课院系名称',
  `teaching_class_id` bigint(20) DEFAULT NULL COMMENT '教学班id',
  `teaching_class_code` varchar(255) DEFAULT NULL COMMENT '教学班编号',
  `teaching_class_name` varchar(255) DEFAULT NULL COMMENT '教学班名称',
  `handle_status` tinyint(4) DEFAULT NULL COMMENT '处理状态；1-待处理 2-挂起 3-无异常 4-确认异常',
  `handle_user_id` bigint(20) DEFAULT NULL COMMENT '处理人id',
  `handle_user_code` varchar(255) DEFAULT NULL COMMENT '处理人编号',
  `handle_user_name` varchar(255) DEFAULT NULL COMMENT '处理人名称',
  `feedback_user_id` bigint(20) DEFAULT NULL COMMENT '反馈人id',
  `feedback_user_code` varchar(255) DEFAULT NULL COMMENT '反馈人编号',
  `feedback_user_name` varchar(255) DEFAULT NULL COMMENT '反馈人名称',
  `feedback_type` tinyint(4) DEFAULT NULL COMMENT '反馈类型；1-不反馈 2-反馈给院系联络人 3-反馈给指定人员',
  `feedback_status` tinyint(4) DEFAULT NULL COMMENT '反馈状态；1-未反馈 2-成功 3-失败 4-无需反馈',
  `handle_description` varchar(512) DEFAULT NULL COMMENT '处理说明',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  `warning_time_day` date GENERATED ALWAYS AS (cast(`warning_time` as date)) STORED COMMENT '预警日期（由 warning_time 计算得出）',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_warning_time` (`warning_time`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_indicator_id` (`indicator_id`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_clro_id` (`clro_id`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_org_id` (`org_id`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_warning_time_org_id` (`org_id`,`warning_time`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_course_id` (`course_id`,`delete_flag`,`tenant_id`) USING BTREE,
  KEY `idx_warning_time_day` (`delete_flag`,`warning_time_day`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='预警-学情预警';

-- ----------------------------
-- Table structure for t_warning_study_record_detail
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_study_record_detail`;
CREATE TABLE `t_warning_study_record_detail` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `study_record_id` bigint(20) NOT NULL COMMENT '学情预警表ID',
  `course_id` bigint(20) DEFAULT NULL COMMENT '课程id',
  `event_time` datetime DEFAULT NULL COMMENT '事件时间',
  `need_att_num` int(11) DEFAULT NULL COMMENT '应到学生数',
  `actual_att_num` int(11) DEFAULT NULL COMMENT '实到学生数',
  `front_row_num` int(11) DEFAULT NULL COMMENT '前排就座人数',
  `middle_row_num` int(11) DEFAULT NULL COMMENT '中排人数',
  `back_row_num` int(11) DEFAULT NULL COMMENT '后排人数',
  `late_num` int(11) DEFAULT NULL COMMENT '迟到学生数',
  `teacher_count` int(11) DEFAULT NULL COMMENT '教师到勤人数',
  `on_time_att_num` int(11) DEFAULT NULL COMMENT '学生准点人数',
  `seat_num` int(11) DEFAULT NULL COMMENT '座位数',
  `rise_num` int(11) DEFAULT NULL COMMENT '抬头人数',
  `att_percent` decimal(20,2) DEFAULT NULL COMMENT '到勤率',
  `front_row_percent` decimal(20,2) DEFAULT NULL COMMENT '前排就座率',
  `rise_percent` decimal(20,2) DEFAULT NULL COMMENT '抬头率',
  `front_full_percent` decimal(20,2) DEFAULT NULL COMMENT '前排满座率',
  `seat_use_percent` decimal(20,2) DEFAULT NULL COMMENT '教室座位利用率',
  `late_percent` decimal(20,2) DEFAULT NULL COMMENT '迟到率',
  `seating_ratio` decimal(20,2) DEFAULT NULL COMMENT '前后排就座比',
  `reading_num` decimal(20,2) DEFAULT NULL COMMENT '阅读人数',
  `phone_use_num` decimal(20,2) DEFAULT NULL COMMENT '使用手机人数',
  `sleep_num` decimal(20,2) DEFAULT NULL COMMENT '趴桌/睡觉人数',
  `concentration` decimal(20,2) DEFAULT NULL COMMENT '专注度',
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
  KEY `idx_course_id` (`course_id`) USING BTREE,
  KEY `inx_event_time` (`event_time`) USING BTREE,
  KEY `idx_update_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_delete_flag` (`delete_flag`) USING BTREE,
  KEY `idx_course_id_event_time` (`course_id`,`event_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='预警-学情预警详情';

-- ----------------------------
-- Table structure for t_warning_study_record_image
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_study_record_image`;
CREATE TABLE `t_warning_study_record_image` (
  `id` bigint(20) NOT NULL COMMENT '主键ID',
  `study_record_id` bigint(20) NOT NULL COMMENT '学情预警表ID',
  `image_id` bigint(20) DEFAULT NULL COMMENT '图片id',
  `image_url` varchar(512) NOT NULL COMMENT '图片地址',
  `capture_time` datetime NOT NULL COMMENT '抓图时间',
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
  KEY `idx_study_record_id` (`study_record_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='预警-学情记录图片表';

-- ----------------------------
-- Table structure for t_warning_study_silence
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_study_silence`;
CREATE TABLE `t_warning_study_silence` (
  `id` bigint(20) NOT NULL COMMENT '主键id',
  `teaching_class_id` bigint(20) DEFAULT NULL COMMENT '教学班id',
  `teaching_class_code` varchar(255) DEFAULT NULL COMMENT '教学班编号',
  `indicator_code` varchar(100) DEFAULT NULL COMMENT '预警指标code',
  `silence_end_time` datetime DEFAULT NULL COMMENT '静默结束时间',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`),
  KEY `idx_teaching_id_indicator_code` (`teaching_class_id`,`indicator_code`),
  KEY `idx_teaching_code_indicator_code` (`teaching_class_code`,`indicator_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预警-学情预警静默表';

-- ----------------------------
-- Table structure for t_warning_teaching_record
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_teaching_record`;
CREATE TABLE `t_warning_teaching_record` (
  `id` bigint(20) NOT NULL COMMENT '主键ID',
  `strategy_id` bigint(20) NOT NULL COMMENT '策略id',
  `indicator_id` bigint(20) NOT NULL COMMENT '预警指标id',
  `indicator_code` varchar(100) DEFAULT NULL COMMENT '预警指标code',
  `indicator_name` varchar(100) DEFAULT NULL COMMENT '预警指标名称',
  `warning_content` varchar(512) DEFAULT NULL COMMENT '预警内容',
  `warning_level` tinyint(4) DEFAULT NULL COMMENT '预警等级；1-高  2-中  3-低 4-提示',
  `warning_time` datetime DEFAULT NULL COMMENT '预警时间',
  `acte_id` bigint(20) DEFAULT NULL COMMENT '学年学期id',
  `course_id` bigint(20) DEFAULT NULL COMMENT '课程id',
  `course_name` varchar(255) DEFAULT NULL COMMENT '课程名称',
  `leti_number` bigint(20) DEFAULT NULL COMMENT '课程节次',
  `course_start_time` datetime DEFAULT NULL COMMENT '课程开始时间',
  `course_end_time` datetime DEFAULT NULL COMMENT '课程结束时间',
  `clro_id` bigint(20) DEFAULT NULL COMMENT '教室id',
  `clro_code` varchar(255) DEFAULT NULL COMMENT '教室编号',
  `clro_name` varchar(255) DEFAULT NULL COMMENT '教室名称',
  `subject_id` bigint(20) DEFAULT NULL COMMENT '科目id',
  `subject_code` varchar(255) DEFAULT NULL COMMENT '科目编号',
  `subject_name` varchar(255) DEFAULT NULL COMMENT '科目名称',
  `org_id` bigint(20) DEFAULT NULL COMMENT '开课院系id',
  `org_code` varchar(255) DEFAULT NULL COMMENT '开课院系编号',
  `org_name` varchar(255) DEFAULT NULL COMMENT '开课院系名称',
  `teaching_class_id` bigint(20) DEFAULT NULL COMMENT '教学班id',
  `teaching_class_code` varchar(255) DEFAULT NULL COMMENT '教学班编号',
  `teaching_class_name` varchar(255) DEFAULT NULL COMMENT '教学班名称',
  `handle_status` tinyint(4) DEFAULT NULL COMMENT '处理状态；1-待处理 2-挂起 3-无异常 4-确认异常',
  `handle_user_id` bigint(20) DEFAULT NULL COMMENT '处理人id',
  `handle_user_code` varchar(255) DEFAULT NULL COMMENT '处理人编号',
  `handle_user_name` varchar(255) DEFAULT NULL COMMENT '处理人名称',
  `feedback_user_id` bigint(20) DEFAULT NULL COMMENT '反馈人id',
  `feedback_user_code` varchar(255) DEFAULT NULL COMMENT '反馈人编号',
  `feedback_user_name` varchar(255) DEFAULT NULL COMMENT '反馈人名称',
  `feedback_type` tinyint(4) DEFAULT NULL COMMENT '反馈类型；1-不反馈 2-反馈给院系联络人 3-反馈给指定人员',
  `feedback_status` tinyint(4) DEFAULT NULL COMMENT '反馈状态；1-未反馈 2-成功 3-失败 4-无需反馈',
  `handle_description` varchar(512) DEFAULT NULL COMMENT '处理说明',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  `warning_time_day` date GENERATED ALWAYS AS (cast(`warning_time` as date)) STORED COMMENT '预警日期（由 warning_time 计算得出）',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_warning_time` (`warning_time`) USING BTREE,
  KEY `idx_indicator_id` (`indicator_id`) USING BTREE,
  KEY `idx_clro_id` (`clro_id`) USING BTREE,
  KEY `idx_org_id` (`org_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_course_id` (`course_id`) USING BTREE,
  KEY `idx_warning_time_day` (`delete_flag`,`warning_time_day`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='预警-教情预警';

-- ----------------------------
-- Table structure for t_warning_teaching_record_detail
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_teaching_record_detail`;
CREATE TABLE `t_warning_teaching_record_detail` (
  `id` bigint(20) NOT NULL COMMENT '主键ID（雪花算法生成）',
  `teaching_record_id` bigint(20) NOT NULL COMMENT '教情预警表ID',
  `course_id` bigint(20) DEFAULT NULL COMMENT '课程id',
  `event_time` datetime DEFAULT NULL COMMENT '事件时间',
  `teacher_count` int(11) DEFAULT NULL COMMENT '实到老师数',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `ai_teacher_name` varchar(255) DEFAULT NULL COMMENT 'ai分析返回的教师姓名',
  `ai_teacher_code` varchar(255) DEFAULT NULL COMMENT 'ai分析返回的教师编码',
  `tenant_id` varchar(255) DEFAULT NULL COMMENT '租户标识',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_course_id` (`course_id`) USING BTREE,
  KEY `inx_event_time` (`event_time`) USING BTREE,
  KEY `idx_update_time` (`last_modified_date_time`) USING BTREE,
  KEY `idx_delete_flag` (`delete_flag`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='预警-教情预警详情';

-- ----------------------------
-- Table structure for t_warning_teaching_record_image
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_teaching_record_image`;
CREATE TABLE `t_warning_teaching_record_image` (
  `id` bigint(20) NOT NULL COMMENT '主键ID',
  `teaching_record_id` bigint(20) NOT NULL COMMENT '教情预警表ID',
  `image_id` bigint(20) DEFAULT NULL COMMENT '图片id',
  `image_url` varchar(512) NOT NULL COMMENT '图片地址',
  `capture_time` datetime NOT NULL COMMENT '抓图时间',
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
  KEY `idx_teaching_record_id` (`teaching_record_id`) USING BTREE,
  KEY `idx_last_modified_date_time` (`last_modified_date_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='预警-教情记录图片表';

-- ----------------------------
-- Table structure for t_warning_teaching_silence
-- ----------------------------
DROP TABLE IF EXISTS `t_warning_teaching_silence`;
CREATE TABLE `t_warning_teaching_silence` (
  `id` bigint(20) NOT NULL COMMENT '主键id',
  `course_id` bigint(20) NOT NULL COMMENT '课程ID',
  `indicator_code` varchar(100) DEFAULT NULL COMMENT '预警指标code',
  `silence_end_time` datetime DEFAULT NULL COMMENT '静默结束时间',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `version` int(11) NOT NULL DEFAULT '1' COMMENT '乐观锁版本号',
  `created_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_date_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `delete_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标志（0：正常，1：删除）',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  PRIMARY KEY (`id`),
  KEY `idx_course_id_indicator_code` (`course_id`,`indicator_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预警-教情预警静默表';

SET FOREIGN_KEY_CHECKS = 1;
