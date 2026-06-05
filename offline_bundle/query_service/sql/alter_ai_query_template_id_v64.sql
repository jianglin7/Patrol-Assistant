ALTER TABLE `ai_metric_definition`
  MODIFY COLUMN `template_id` varchar(64) DEFAULT NULL COMMENT '对应模板ID';

ALTER TABLE `ai_query_template_registry`
  MODIFY COLUMN `template_id` varchar(64) NOT NULL COMMENT '模板ID';

ALTER TABLE `ai_query_audit_log`
  MODIFY COLUMN `template_id` varchar(64) NOT NULL COMMENT '模板ID';
