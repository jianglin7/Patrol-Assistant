DROP TABLE IF EXISTS `ai_metric_definition`;
CREATE TABLE `ai_metric_definition` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `metric_code` varchar(64) NOT NULL COMMENT '指标编码',
  `metric_name` varchar(255) NOT NULL COMMENT '指标名称',
  `metric_definition` text COMMENT '指标定义',
  `stat_rule` text COMMENT '统计口径',
  `source_tables` varchar(500) DEFAULT NULL COMMENT '来源表',
  `source_fields` varchar(500) DEFAULT NULL COMMENT '来源字段',
  `template_id` varchar(64) DEFAULT NULL COMMENT '对应模板ID',
  `default_time_range` varchar(64) DEFAULT NULL COMMENT '默认时间范围',
  `tenant_id` varchar(50) NOT NULL DEFAULT 'default' COMMENT '租户编号',
  `created_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_metric_code_tenant` (`metric_code`,`tenant_id`),
  KEY `idx_template_id` (`template_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI指标定义表';

DROP TABLE IF EXISTS `ai_query_template_registry`;
CREATE TABLE `ai_query_template_registry` (
  `template_id` varchar(64) NOT NULL COMMENT '模板ID',
  `tenant_id` varchar(50) NOT NULL DEFAULT 'default' COMMENT '租户编号',
  `template_name` varchar(255) NOT NULL COMMENT '模板名称',
  `template_category` varchar(64) DEFAULT NULL COMMENT '模板分类',
  `template_sql` longtext NOT NULL COMMENT '模板SQL',
  `param_schema` json DEFAULT NULL COMMENT '参数定义',
  `result_schema` json DEFAULT NULL COMMENT '结果定义',
  `enabled_flag` tinyint(4) NOT NULL DEFAULT '1' COMMENT '是否启用',
  `created_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`template_id`,`tenant_id`),
  KEY `idx_enabled_flag` (`enabled_flag`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI查询模板注册表';

DROP TABLE IF EXISTS `ai_query_audit_log`;
CREATE TABLE `ai_query_audit_log` (
  `request_id` varchar(64) NOT NULL COMMENT '请求ID',
  `user_id` varchar(64) DEFAULT NULL COMMENT '用户ID',
  `tenant_id` varchar(50) NOT NULL COMMENT '租户编号',
  `template_id` varchar(64) NOT NULL COMMENT '模板ID',
  `request_params` json DEFAULT NULL COMMENT '原始请求参数',
  `normalized_params` json DEFAULT NULL COMMENT '标准化参数',
  `result_count` int(11) DEFAULT '0' COMMENT '返回条数',
  `success_flag` tinyint(4) NOT NULL DEFAULT '0' COMMENT '是否成功',
  `error_code` varchar(64) DEFAULT NULL COMMENT '错误码',
  `error_msg` varchar(2000) DEFAULT NULL COMMENT '错误信息',
  `duration_ms` int(11) DEFAULT NULL COMMENT '执行耗时毫秒',
  `created_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`request_id`),
  KEY `idx_template_created_time` (`template_id`,`created_time`),
  KEY `idx_tenant_created_time` (`tenant_id`,`created_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI查询审计日志表';
