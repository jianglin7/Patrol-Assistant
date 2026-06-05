/*
 Navicat Premium Dump SQL

 Source Server         : seacraft
 Source Server Type    : MySQL
 Source Server Version : 50744 (5.7.44-log)
 Source Host           : 10.80.6.54:3306
 Source Schema         : jy_course_he

 Target Server Type    : MySQL
 Target Server Version : 50744 (5.7.44-log)
 File Encoding         : 65001

 Date: 18/05/2026 13:32:49
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for t_academic_term
-- ----------------------------
DROP TABLE IF EXISTS `t_academic_term`;
CREATE TABLE `t_academic_term` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `acye_id` bigint(20) DEFAULT NULL COMMENT '学年ID',
  `acte_term` int(11) DEFAULT NULL COMMENT '学期',
  `acte_code` varchar(50) DEFAULT NULL COMMENT '学期编号',
  `acte_name` varchar(50) DEFAULT NULL COMMENT '学期名称',
  `acte_begin_date` datetime DEFAULT NULL COMMENT '学期开始日',
  `acte_end_date` datetime DEFAULT NULL COMMENT '学期结束日',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_academic_term_acye_id` (`acye_id`) USING BTREE,
  KEY `idx_academic_term_acte_begin_date_acte_end_date` (`acte_begin_date`,`acte_end_date`) USING BTREE,
  KEY `idx_academic_term_acte_end_date` (`acte_end_date`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8 COMMENT='学期表';

-- ----------------------------
-- Table structure for t_academic_year
-- ----------------------------
DROP TABLE IF EXISTS `t_academic_year`;
CREATE TABLE `t_academic_year` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `acye_begin_year` int(11) DEFAULT NULL COMMENT '学年开始年',
  `acye_end_year` int(11) DEFAULT NULL COMMENT '学年结束年',
  `acye_code` varchar(50) DEFAULT NULL COMMENT '学年编号',
  `acye_name` varchar(50) DEFAULT NULL COMMENT '学年名称',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_academic_year_acye_begin_year_acye_end_year` (`acye_begin_year`,`acye_end_year`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8 COMMENT='学年表';

-- ----------------------------
-- Table structure for t_administrative_class
-- ----------------------------
DROP TABLE IF EXISTS `t_administrative_class`;
CREATE TABLE `t_administrative_class` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `adcl_code` varchar(100) DEFAULT NULL COMMENT '行政班编号',
  `adcl_name` varchar(200) DEFAULT NULL COMMENT '行政班名称',
  `adcl_grade` varchar(50) DEFAULT NULL COMMENT '年级',
  `majo_id` bigint(20) DEFAULT NULL COMMENT '专业id',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_adcl_code` (`adcl_code`) USING BTREE,
  KEY `idx_majo_id` (`majo_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8 COMMENT='行政班';

-- ----------------------------
-- Table structure for t_building
-- ----------------------------
DROP TABLE IF EXISTS `t_building`;
CREATE TABLE `t_building` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `buil_code` varchar(50) DEFAULT NULL COMMENT '教学楼编号',
  `buil_name` varchar(50) DEFAULT NULL COMMENT '教学楼名称',
  `buil_floor_count` int(11) DEFAULT NULL COMMENT '教学楼总层数',
  `buil_first_floor_num` int(11) DEFAULT NULL COMMENT '教学楼起始楼层数',
  `camp_id` bigint(20) DEFAULT NULL COMMENT '校区id',
  `buil_sort` int(11) DEFAULT '0' COMMENT '教学楼排序',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=92 DEFAULT CHARSET=utf8 COMMENT='教学楼表';

-- ----------------------------
-- Table structure for t_campus
-- ----------------------------
DROP TABLE IF EXISTS `t_campus`;
CREATE TABLE `t_campus` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `remarks` varchar(256) DEFAULT NULL COMMENT '备注',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `camp_code` varchar(50) DEFAULT NULL COMMENT '校区编码',
  `camp_name` varchar(50) DEFAULT NULL COMMENT '校区名称',
  `extend_1` varchar(50) DEFAULT NULL COMMENT '扩展字段1',
  `extend_2` varchar(50) DEFAULT NULL COMMENT '扩展字段2',
  `camp_photo` varchar(256) DEFAULT NULL COMMENT '校区图片',
  `camp_sort` int(11) DEFAULT '0' COMMENT '校区排序',
  `domain_name` varchar(1000) DEFAULT NULL COMMENT '校区域名地址',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=80 DEFAULT CHARSET=utf8 COMMENT='课表组件-校区';

-- ----------------------------
-- Table structure for t_classroom
-- ----------------------------
DROP TABLE IF EXISTS `t_classroom`;
CREATE TABLE `t_classroom` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `buil_id` bigint(20) DEFAULT NULL COMMENT '教学楼ID',
  `clro_building_floor_num` int(11) DEFAULT NULL COMMENT '教室所在教学楼楼层',
  `clro_code` varchar(100) DEFAULT NULL COMMENT '教室编号',
  `clro_name` varchar(100) DEFAULT NULL COMMENT '教室名称',
  `clro_type` smallint(6) DEFAULT '0' COMMENT '教室类型：0：未知；1：云可视教室（IPC和编码器或者SVR2730+）；2：瞭望教室（SVR）；3：第三方教室（IPC和编码器）；',
  `clro_device_type` smallint(6) DEFAULT '0' COMMENT '教室设备类型：0：未知；1：IPC和编码器；2：SVR2730+；3：SVR；',
  `remark` varchar(200) DEFAULT NULL COMMENT '备注',
  `actual_att_error_rate` decimal(20,10) DEFAULT NULL COMMENT 'tias实到学生数误差率',
  `clro_seat_count` int(11) DEFAULT NULL COMMENT '教室座位数',
  `clro_front_seat_count` int(11) DEFAULT NULL COMMENT '教室前排座位数',
  `clro_sort` int(11) DEFAULT '0' COMMENT '教室排序',
  `clro_use_type` int(11) DEFAULT '1' COMMENT ' 1：线上教室 2：线下教室',
  `space_type_id` bigint(20) DEFAULT NULL COMMENT '关联空间类型ID',
  `space_label_id` bigint(20) DEFAULT NULL COMMENT '关联空间标签ID',
  `clro_frontend_transfer` tinyint(4) DEFAULT NULL COMMENT '是否前端转写,0：否;1：是',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_classroom_buil_id` (`buil_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=5016 DEFAULT CHARSET=utf8 COMMENT='教室表';

-- ----------------------------
-- Table structure for t_classroom_interact_info
-- ----------------------------
DROP TABLE IF EXISTS `t_classroom_interact_info`;
CREATE TABLE `t_classroom_interact_info` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `classroom_id` bigint(20) DEFAULT NULL COMMENT '教室id',
  `able` smallint(6) DEFAULT '0' COMMENT '是否能够互动 0不可以 1可以',
  `projection` varchar(2) DEFAULT NULL COMMENT '投影/一体机',
  `reverse_display` varchar(2) DEFAULT NULL COMMENT '反显/抬头屏',
  `output_port` varchar(2) DEFAULT NULL COMMENT 'SRV本地输出',
  `supcon_ip` varchar(20) DEFAULT NULL COMMENT '中控ip地址',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=84 DEFAULT CHARSET=utf8mb4 COMMENT='教室互动设备信息';

-- ----------------------------
-- Table structure for t_classroom_space_label
-- ----------------------------
DROP TABLE IF EXISTS `t_classroom_space_label`;
CREATE TABLE `t_classroom_space_label` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `space_label_name` varchar(100) NOT NULL COMMENT '空间标签名称',
  `space_label_type` smallint(6) DEFAULT NULL COMMENT '空间标签类型,1-正向标签，2-中性标签，3-负向标签',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_recycle_sign` (`recycle_sign`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='空间标签管理';

-- ----------------------------
-- Table structure for t_classroom_space_type
-- ----------------------------
DROP TABLE IF EXISTS `t_classroom_space_type`;
CREATE TABLE `t_classroom_space_type` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `space_type_name` varchar(100) NOT NULL COMMENT '空间类型名称',
  `is_default` tinyint(1) DEFAULT '0' COMMENT '是否为默认空间类型',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_recycle_sign` (`recycle_sign`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='空间类型管理';

-- ----------------------------
-- Table structure for t_course
-- ----------------------------
DROP TABLE IF EXISTS `t_course`;
CREATE TABLE `t_course` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `clro_id` bigint(20) DEFAULT NULL COMMENT '教室ID',
  `leti_id` bigint(20) DEFAULT NULL COMMENT '节次ID',
  `tecl_id` bigint(20) DEFAULT NULL COMMENT '教学班ID',
  `cour_name` varchar(255) DEFAULT NULL COMMENT '课程名称',
  `cour_begin_time` datetime DEFAULT NULL COMMENT '开时时间',
  `cour_end_time` datetime DEFAULT NULL COMMENT '结束时间',
  `cour_description` text COMMENT '课程简介(本节课程简介)',
  `cour_play_count` bigint(20) DEFAULT '0' COMMENT '课程播放次数',
  `cour_play_peo_count` bigint(20) DEFAULT '0' COMMENT '课程播放人数',
  `live_view_peo_count` bigint(20) DEFAULT '0' COMMENT '直播观看人数',
  `live_view_count` bigint(20) DEFAULT '0' COMMENT '直播观看次数',
  `data_sources` bigint(20) DEFAULT '1' COMMENT '数据来源 0教务排课 1平台手动排课 2校正规则（手动调整、教务调课表）',
  `clro_enable` int(11) DEFAULT '1' COMMENT '教室是否开放 0 关闭 1 开放',
  `source_type` int(11) DEFAULT '0' COMMENT '0 不区分 1 习题课',
  `cour_day` date GENERATED ALWAYS AS (cast(`cour_begin_time` as date)) STORED COMMENT '课程日期（由 cour_begin_time 计算得出）',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_course_clro_id` (`clro_id`) USING BTREE,
  KEY `idx_course_leti_id` (`leti_id`) USING BTREE,
  KEY `idx_course_tecl_id` (`tecl_id`) USING BTREE,
  KEY `idx_course_cour_begin_time_cour_end_time` (`cour_begin_time`,`cour_end_time`) USING BTREE,
  KEY `idx_course_tecl_id_cour_begin_time_cour_end_time` (`tecl_id`,`cour_begin_time`,`cour_end_time`) USING BTREE,
  KEY `idx_course_clro_id_cour_begin_time_cour_end_time` (`clro_id`,`cour_begin_time`,`cour_end_time`) USING BTREE,
  KEY `idx_multi` (`clro_id`,`cour_day`,`tenant_org_code`,`recycle_sign`,`clro_enable`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=590603 DEFAULT CHARSET=utf8 COMMENT='课程表';

-- ----------------------------
-- Table structure for t_course_source_type
-- ----------------------------
DROP TABLE IF EXISTS `t_course_source_type`;
CREATE TABLE `t_course_source_type` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `cour_id` bigint(20) DEFAULT NULL COMMENT '课程id',
  `source_type` smallint(6) DEFAULT NULL COMMENT '来源类型 0 不区分 1 习题课',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_cour_id` (`cour_id`) USING BTREE,
  KEY `idx_source_type` (`source_type`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='课程-来源关联表';

-- ----------------------------
-- Table structure for t_course_teacher
-- ----------------------------
DROP TABLE IF EXISTS `t_course_teacher`;
CREATE TABLE `t_course_teacher` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `cour_id` bigint(20) DEFAULT NULL COMMENT '课程id',
  `user_id` bigint(20) DEFAULT NULL COMMENT '教师用户id',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_course_teacher_cour_id` (`cour_id`) USING BTREE,
  KEY `idx_course_teacher_user_id` (`user_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=222669 DEFAULT CHARSET=utf8 COMMENT='课程表';

-- ----------------------------
-- Table structure for t_exam
-- ----------------------------
DROP TABLE IF EXISTS `t_exam`;
CREATE TABLE `t_exam` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT NULL COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `sche_id` bigint(20) NOT NULL COMMENT '时间计划表id',
  `exam_name` varchar(200) DEFAULT NULL COMMENT '考试名称',
  `exam_type_id` bigint(6) DEFAULT NULL COMMENT '考试类型id',
  `exam_class_name` varchar(200) DEFAULT NULL COMMENT '考试班级名称',
  `exam_room_number` varchar(200) DEFAULT NULL COMMENT '考试号',
  `exam_count` int(11) DEFAULT NULL COMMENT '考试人数',
  `exam_video_retention_date` datetime DEFAULT NULL COMMENT '视频过期时间,NULL为永久留存',
  `exam_video_status` smallint(6) DEFAULT '0' COMMENT '默认为0:初始化; 1,生成中; 2,生成完成; 3,生成失败; 4,无视频; 5,视频时长异常',
  `exam_video_recycle` smallint(6) DEFAULT '0' COMMENT '资源删除状态 0-正常；1-删除',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_sche_id` (`sche_id`) USING BTREE,
  KEY `idx_exam_room_number` (`exam_room_number`) USING BTREE,
  KEY `idx_exam_class_name` (`exam_class_name`) USING BTREE,
  KEY `idx_exam_name` (`exam_name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=34 DEFAULT CHARSET=utf8 COMMENT='考试表';

-- ----------------------------
-- Table structure for t_exam_proctor
-- ----------------------------
DROP TABLE IF EXISTS `t_exam_proctor`;
CREATE TABLE `t_exam_proctor` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT NULL COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `exam_id` bigint(20) NOT NULL COMMENT '时间计划表id',
  `expr_user_id` bigint(20) DEFAULT NULL COMMENT '监考老师用户id',
  `expr_user_code` varchar(200) DEFAULT NULL COMMENT '监考老师编号',
  `expr_user_name` varchar(200) DEFAULT NULL COMMENT '监考老师用户名',
  `expr_type` smallint(6) DEFAULT '0' COMMENT '监考员类型:0 校内; 2 校外;',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_exam_id` (`exam_id`,`expr_user_id`) USING BTREE,
  KEY `idx_ex_pr_user_name` (`expr_user_name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=54 DEFAULT CHARSET=utf8 COMMENT='考试监考老师表';

-- ----------------------------
-- Table structure for t_exam_type
-- ----------------------------
DROP TABLE IF EXISTS `t_exam_type`;
CREATE TABLE `t_exam_type` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT NULL COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `exty_sort` int(11) DEFAULT NULL COMMENT '考试类型序号',
  `exty_name` varchar(200) DEFAULT NULL COMMENT '考试类型名称',
  `exty_save_days` int(11) DEFAULT NULL COMMENT '考试录像保存天数',
  `exty_storage_names` text COMMENT '录像存储名称,逗号分割, NULL表示不指定',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8 COMMENT='考试类型';

-- ----------------------------
-- Table structure for t_expert
-- ----------------------------
DROP TABLE IF EXISTS `t_expert`;
CREATE TABLE `t_expert` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `insert_time` datetime DEFAULT NULL COMMENT '插入时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '回收站标记',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '租户编码',
  `user_id` bigint(20) DEFAULT NULL COMMENT '用户id',
  `effective_status` smallint(6) DEFAULT NULL COMMENT '有效状态 0-无效 1-有效',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_user_id` (`user_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=233 DEFAULT CHARSET=utf8mb4 COMMENT='专家';

-- ----------------------------
-- Table structure for t_expert_counted_contain_role
-- ----------------------------
DROP TABLE IF EXISTS `t_expert_counted_contain_role`;
CREATE TABLE `t_expert_counted_contain_role` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `insert_time` datetime DEFAULT NULL COMMENT '插入时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '回收站标记',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `lesson_org_role_id` bigint(20) NOT NULL COMMENT '听课组织角色id',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_lesson_org_role_id` (`lesson_org_role_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1045 DEFAULT CHARSET=utf8mb4 COMMENT='专家数量统计-需包含的角色';

-- ----------------------------
-- Table structure for t_expert_lesson_org
-- ----------------------------
DROP TABLE IF EXISTS `t_expert_lesson_org`;
CREATE TABLE `t_expert_lesson_org` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `insert_time` datetime DEFAULT NULL COMMENT '插入时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '回收站标记',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '租户编码',
  `lesson_org_id` bigint(20) NOT NULL COMMENT '听课组织id',
  `expert_id` bigint(20) NOT NULL COMMENT '专家id',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_lesson_org_id` (`lesson_org_id`) USING BTREE,
  KEY `idx_expert_id` (`expert_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=802 DEFAULT CHARSET=utf8mb4 COMMENT='专家-听课组织';

-- ----------------------------
-- Table structure for t_expert_lesson_org_role
-- ----------------------------
DROP TABLE IF EXISTS `t_expert_lesson_org_role`;
CREATE TABLE `t_expert_lesson_org_role` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `insert_time` datetime DEFAULT NULL COMMENT '插入时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '回收站标记',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '租户编码',
  `lesson_org_role_id` bigint(20) NOT NULL COMMENT '听课组织角色id',
  `expert_id` bigint(20) NOT NULL COMMENT '专家id',
  `begin_date` date DEFAULT NULL COMMENT '角色有效期开始时间',
  `end_date` date DEFAULT NULL COMMENT '角色有效期结束时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_lesson_org_role_id` (`lesson_org_role_id`) USING BTREE,
  KEY `idx_expert_id` (`expert_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1184 DEFAULT CHARSET=utf8mb4 COMMENT='专家-角色';

-- ----------------------------
-- Table structure for t_interactive_course
-- ----------------------------
DROP TABLE IF EXISTS `t_interactive_course`;
CREATE TABLE `t_interactive_course` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT NULL COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `cour_id` bigint(20) DEFAULT NULL COMMENT '课程id',
  `interactive_type` smallint(6) DEFAULT NULL COMMENT '远程互动下的主听讲模式 0: 不固定,1:主讲教室，2:听课教室',
  `interactive_id` varchar(200) DEFAULT NULL COMMENT '互动教学分组id(相同id的互动排课为同一组远程互动教学)',
  `clro_id` bigint(20) DEFAULT NULL COMMENT '教室id',
  `start_time` datetime DEFAULT NULL COMMENT '互动开始时间',
  `end_time` datetime DEFAULT NULL COMMENT '互动结束时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `index_cour_id` (`cour_id`) USING BTREE,
  KEY `index_interactive_id_time` (`interactive_id`,`start_time`,`end_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='互动课表';

-- ----------------------------
-- Table structure for t_label
-- ----------------------------
DROP TABLE IF EXISTS `t_label`;
CREATE TABLE `t_label` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `labe_group` varchar(100) DEFAULT NULL COMMENT '标签组名称',
  `labe_name` varchar(100) DEFAULT NULL COMMENT '标签名称',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_label_labe_group` (`labe_group`) USING BTREE,
  KEY `idx_label_labe_name` (`labe_name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=47 DEFAULT CHARSET=utf8 COMMENT='标签表';

-- ----------------------------
-- Table structure for t_label_subject
-- ----------------------------
DROP TABLE IF EXISTS `t_label_subject`;
CREATE TABLE `t_label_subject` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `labe_id` bigint(20) DEFAULT NULL COMMENT '标签id',
  `subj_id` bigint(20) DEFAULT NULL COMMENT '科目id',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_label_subject_labe_id` (`labe_id`) USING BTREE,
  KEY `idx_label_subject_subj_id` (`subj_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=327 DEFAULT CHARSET=utf8 COMMENT='标签科目中间表';

-- ----------------------------
-- Table structure for t_label_teaching_class
-- ----------------------------
DROP TABLE IF EXISTS `t_label_teaching_class`;
CREATE TABLE `t_label_teaching_class` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `labe_id` bigint(20) DEFAULT NULL COMMENT '标签id',
  `tecl_id` bigint(20) DEFAULT NULL COMMENT '教学班id',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_label_teaching_class_labe_id` (`labe_id`) USING BTREE,
  KEY `idx_label_teaching_class_tecl_id` (`tecl_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=510 DEFAULT CHARSET=utf8 COMMENT='标签教学班中间表';

-- ----------------------------
-- Table structure for t_lesson_org_role
-- ----------------------------
DROP TABLE IF EXISTS `t_lesson_org_role`;
CREATE TABLE `t_lesson_org_role` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `insert_time` datetime DEFAULT NULL COMMENT '插入时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '回收站标记',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `lesson_org_id` bigint(20) NOT NULL COMMENT '听课组织id',
  `role_code` varchar(50) DEFAULT NULL COMMENT '角色编号',
  `role_name` varchar(100) DEFAULT NULL COMMENT '角色名称',
  `course_view` varchar(50) DEFAULT NULL COMMENT '查看课程（多个逗号隔开） 1 本科生  2 研究生',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_lesson_org_id_role_code` (`lesson_org_id`,`role_code`) USING BTREE,
  KEY `idx_role_code` (`role_code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2087 DEFAULT CHARSET=utf8mb4 COMMENT='听课组织角色';

-- ----------------------------
-- Table structure for t_lesson_org_role_resource
-- ----------------------------
DROP TABLE IF EXISTS `t_lesson_org_role_resource`;
CREATE TABLE `t_lesson_org_role_resource` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `insert_time` datetime DEFAULT NULL COMMENT '插入时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '回收站标记',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `lesson_org_id` bigint(20) NOT NULL COMMENT '听课组织id',
  `lesson_org_role_id` bigint(20) NOT NULL COMMENT '听课组织角色id',
  `apply_code` varchar(50) DEFAULT NULL COMMENT '应用编码',
  `resource_code` varchar(50) DEFAULT NULL COMMENT '资源编码',
  `checked` smallint(6) DEFAULT '0' COMMENT '是否选中 0-否 1-是',
  `data_privilege_type` smallint(6) DEFAULT NULL COMMENT '数据权限 1-本级听课组织  2-所属听课组织及其下级组织',
  `record_view_types` varchar(50) DEFAULT NULL COMMENT '评价记录视图 1-综合视图 2-我管理的任务评价 3-我院系的所有评价 多个用逗号隔开',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_lesson_role_id_apply_code` (`lesson_org_role_id`,`apply_code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=98235 DEFAULT CHARSET=utf8mb4 COMMENT='听课组织资源';

-- ----------------------------
-- Table structure for t_lesson_organization
-- ----------------------------
DROP TABLE IF EXISTS `t_lesson_organization`;
CREATE TABLE `t_lesson_organization` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `insert_time` datetime DEFAULT NULL COMMENT '插入时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '回收站标记',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '租户编码',
  `org_id` bigint(20) NOT NULL COMMENT '机构id',
  `org_id_path` varchar(2000) DEFAULT NULL COMMENT '机构id路径',
  `effective_status` smallint(6) DEFAULT NULL COMMENT '听课组织有效状态 0-无效 1-有效',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_org_id` (`org_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=336 DEFAULT CHARSET=utf8mb4 COMMENT='听课组织';

-- ----------------------------
-- Table structure for t_lesson_time
-- ----------------------------
DROP TABLE IF EXISTS `t_lesson_time`;
CREATE TABLE `t_lesson_time` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `leti_number` smallint(6) DEFAULT NULL COMMENT '课程节次',
  `leti_type_id` bigint(20) DEFAULT NULL COMMENT '课程时间类型id',
  `leti_begin_time` varchar(8) DEFAULT NULL COMMENT '课程开始时间(型如：08:00:00)',
  `leti_end_time` varchar(8) DEFAULT NULL COMMENT '课程结束时间(型如：08:45:00)',
  `leti_begin_time_long` int(11) DEFAULT NULL COMMENT '课程开始时间(用于比较)',
  `leti_end_time_long` int(11) DEFAULT NULL COMMENT '课程结束时间(用于比较)',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=479 DEFAULT CHARSET=utf8 COMMENT='课程时间表';

-- ----------------------------
-- Table structure for t_lesson_type
-- ----------------------------
DROP TABLE IF EXISTS `t_lesson_type`;
CREATE TABLE `t_lesson_type` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `lety_name` varchar(100) DEFAULT NULL COMMENT '节次类型名称',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_lesson_type_lety_name` (`lety_name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=94 DEFAULT CHARSET=utf8 COMMENT='节次类型表';

-- ----------------------------
-- Table structure for t_lesson_type_classroom_relation
-- ----------------------------
DROP TABLE IF EXISTS `t_lesson_type_classroom_relation`;
CREATE TABLE `t_lesson_type_classroom_relation` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `lesson_type_id` bigint(20) NOT NULL COMMENT '课程时间类型id',
  `clro_id` bigint(20) NOT NULL COMMENT '教室id',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_lesson_type_clro_id` (`lesson_type_id`,`clro_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=112 DEFAULT CHARSET=utf8 ROW_FORMAT=DYNAMIC COMMENT='节次类型与教室绑定关系';

-- ----------------------------
-- Table structure for t_lesson_type_effective_time
-- ----------------------------
DROP TABLE IF EXISTS `t_lesson_type_effective_time`;
CREATE TABLE `t_lesson_type_effective_time` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `lesson_type_id` bigint(20) NOT NULL COMMENT '课程时间类型id',
  `status` smallint(6) DEFAULT '0' COMMENT '节次计划指定生效日期是否开启,默认为0:不开启;1,开启',
  `start_time` varchar(10) DEFAULT NULL COMMENT '节次类型生效的开始时间,格式为月-日',
  `end_time` varchar(10) DEFAULT NULL COMMENT '节次类型生效的结束时间,格式为月-日',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_lesson_type_id_start_end_time` (`lesson_type_id`,`start_time`,`end_time`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=85 DEFAULT CHARSET=utf8 ROW_FORMAT=DYNAMIC COMMENT='节次类型生效时间';

-- ----------------------------
-- Table structure for t_lexicon_type
-- ----------------------------
DROP TABLE IF EXISTS `t_lexicon_type`;
CREATE TABLE `t_lexicon_type` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `insert_time` datetime DEFAULT NULL COMMENT '插入时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '回收站标记',
  `remarks` varchar(256) DEFAULT NULL COMMENT '备注',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '租户编码',
  `lety_name` varchar(50) DEFAULT NULL COMMENT '类别名称',
  `lety_code` varchar(50) DEFAULT NULL COMMENT '词库编码',
  `extend_1` varchar(50) DEFAULT NULL COMMENT '扩展字段1',
  `extend_2` varchar(50) DEFAULT NULL COMMENT '扩展字段2',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='督导-词库类别';

-- ----------------------------
-- Table structure for t_lti_field_mapping
-- ----------------------------
DROP TABLE IF EXISTS `t_lti_field_mapping`;
CREATE TABLE `t_lti_field_mapping` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `lti_course_id` varchar(50) NOT NULL COMMENT 'lti课程id',
  `local_user_code` varchar(100) NOT NULL COMMENT '教师编号',
  `local_subj_code` varchar(100) NOT NULL COMMENT '科目编号',
  `local_tecl_code` varchar(100) NOT NULL COMMENT '教学班编号',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `insert_datetime` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '插入时间',
  `update_datetime` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `recycle_sign` varchar(6) NOT NULL DEFAULT '0' COMMENT '逻辑删除状态',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_lti_lti_course_id` (`lti_course_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='LTI 字段映射';

-- ----------------------------
-- Table structure for t_major
-- ----------------------------
DROP TABLE IF EXISTS `t_major`;
CREATE TABLE `t_major` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `majo_code` varchar(100) DEFAULT NULL COMMENT '专业编号',
  `majo_name` varchar(200) DEFAULT NULL COMMENT '专业名称',
  `orga_id` bigint(20) DEFAULT NULL COMMENT '所属机构id',
  `majo_type` varchar(255) DEFAULT NULL COMMENT '专业类型',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_majo_code` (`majo_code`) USING BTREE,
  KEY `idx_orga_id` (`orga_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8 COMMENT='专业表';

-- ----------------------------
-- Table structure for t_multi_organization_user
-- ----------------------------
DROP TABLE IF EXISTS `t_multi_organization_user`;
CREATE TABLE `t_multi_organization_user` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT NULL COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(255) DEFAULT NULL COMMENT '所属租户组织编号',
  `user_id` bigint(20) DEFAULT NULL COMMENT '用户id',
  `user_code` varchar(255) DEFAULT NULL COMMENT '用户编码',
  `orga_id` bigint(20) DEFAULT NULL COMMENT '组织id',
  `orga_code` varchar(255) DEFAULT NULL COMMENT '组织编码',
  `end_date` date DEFAULT NULL COMMENT '有效期结束时间',
  `role_code` varchar(255) DEFAULT NULL COMMENT '角色编码',
  `role_privilege` smallint(6) DEFAULT '1' COMMENT '角色权限',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `user_id` (`user_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2227 DEFAULT CHARSET=utf8mb4 COMMENT='用户-多院系关系表';

-- ----------------------------
-- Table structure for t_non_evaluation_student
-- ----------------------------
DROP TABLE IF EXISTS `t_non_evaluation_student`;
CREATE TABLE `t_non_evaluation_student` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `eval_scope` tinyint(1) NOT NULL COMMENT '不参评范围',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `insert_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='不参评学生记录表';

-- ----------------------------
-- Table structure for t_organization
-- ----------------------------
DROP TABLE IF EXISTS `t_organization`;
CREATE TABLE `t_organization` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `orga_parent_id` bigint(20) DEFAULT NULL COMMENT '上级机构ID',
  `orga_level` smallint(6) DEFAULT NULL COMMENT '机构级别',
  `orga_code` varchar(100) DEFAULT NULL COMMENT '机构编号',
  `orga_name` varchar(100) DEFAULT NULL COMMENT '机构名称',
  `show_state` smallint(5) DEFAULT '1' COMMENT '前端展示 0否 1 是',
  `order_num` int(11) DEFAULT NULL COMMENT '组织顺序',
  `lesson_org_sign` smallint(6) DEFAULT '0' COMMENT '是否是听课组织 0-否 1-是',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_organization_orga_code` (`orga_code`) USING BTREE,
  KEY `idx_organization_orga_name` (`orga_name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=11208 DEFAULT CHARSET=utf8 COMMENT='组织机构表';

-- ----------------------------
-- Table structure for t_organization_level
-- ----------------------------
DROP TABLE IF EXISTS `t_organization_level`;
CREATE TABLE `t_organization_level` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `orle_name` varchar(100) DEFAULT NULL COMMENT '级别名称',
  `orle_level` smallint(6) DEFAULT NULL COMMENT '级别:1, 2, 3, ... , 8;',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8 COMMENT='组织机构级别表';

-- ----------------------------
-- Table structure for t_organization_user
-- ----------------------------
DROP TABLE IF EXISTS `t_organization_user`;
CREATE TABLE `t_organization_user` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `user_id` bigint(20) DEFAULT NULL COMMENT '用户ID',
  `orga_id` bigint(20) DEFAULT NULL COMMENT '组织机构ID',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_organization_user_user_id_orga_id` (`user_id`,`orga_id`) USING BTREE,
  KEY `idx_organization_user_orga_id` (`orga_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=404168 DEFAULT CHARSET=utf8 COMMENT='组织机构用户关系表';

-- ----------------------------
-- Table structure for t_resource_data
-- ----------------------------
DROP TABLE IF EXISTS `t_resource_data`;
CREATE TABLE `t_resource_data` (
  `id` varchar(50) NOT NULL COMMENT '主键',
  `parent_id` varchar(50) DEFAULT NULL COMMENT '父类id',
  `insert_time` datetime DEFAULT NULL COMMENT '插入时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '回收站标记',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '租户编码',
  `client_sign` varchar(300) NOT NULL COMMENT '应用标识',
  `resource_sign` varchar(300) NOT NULL COMMENT '资源标识',
  `resource_name` varchar(300) DEFAULT NULL COMMENT '资源名称',
  `resource_en_name` varchar(300) DEFAULT NULL COMMENT '资源英文名称',
  `resource_type` varchar(50) DEFAULT NULL COMMENT '资源类型 memu：菜单 tab：tab标签 api：接口 opt：操作',
  `resource_url` varchar(1000) DEFAULT NULL COMMENT '资源url',
  `resource_status` smallint(6) DEFAULT '1' COMMENT '资源状态 0-禁用 1-启用',
  `level_index` smallint(6) DEFAULT '1' COMMENT '资源层级',
  `sort_index` int(11) DEFAULT '1' COMMENT '排序值',
  `fields` varchar(2000) DEFAULT NULL COMMENT '拓展字段 jsonArray 示例：[{"name": "isLink","description": "true"}]',
  `icon` varchar(300) DEFAULT NULL COMMENT '资源icon',
  `record_view_types` varchar(50) DEFAULT NULL COMMENT '评价记录视图 1-综合视图 2-我管理的任务评价 3-我院系的所有评价 多个用逗号隔开',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_resource_sign` (`resource_sign`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资源菜单表';

-- ----------------------------
-- Table structure for t_role
-- ----------------------------
DROP TABLE IF EXISTS `t_role`;
CREATE TABLE `t_role` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT NULL COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `role_code` varchar(50) DEFAULT NULL COMMENT '角色编码',
  `role_type` smallint(6) DEFAULT NULL COMMENT '角色类型 1 校级 2 院级 3 专项',
  `course_view` varchar(50) DEFAULT NULL COMMENT '查看课程（多个逗号隔开） 1 本科生  2 研究生',
  `app_code` varchar(255) DEFAULT NULL COMMENT '项目标识',
  `create_user_id` bigint(20) DEFAULT NULL COMMENT '创建人id',
  `update_user_id` bigint(20) DEFAULT NULL COMMENT '更新人id',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `last_modified_by` varchar(50) DEFAULT NULL COMMENT '最后修改人',
  `role_name` varchar(255) DEFAULT NULL COMMENT '角色名称',
  `role_desc` varchar(255) DEFAULT NULL COMMENT '角色描述',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `role_code` (`role_code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=6837 DEFAULT CHARSET=utf8 COMMENT='角色表';

-- ----------------------------
-- Table structure for t_schedule
-- ----------------------------
DROP TABLE IF EXISTS `t_schedule`;
CREATE TABLE `t_schedule` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT NULL COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `clro_id` bigint(20) NOT NULL COMMENT '教室id',
  `sche_begin_time` datetime DEFAULT NULL COMMENT '开始时间',
  `sche_end_time` datetime DEFAULT NULL COMMENT '结束时间',
  `sche_type` smallint(6) DEFAULT '0' COMMENT '占用类型:0 课程安排; 1 考试安排;',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_clro_id_begin_end_time` (`clro_id`,`sche_begin_time`,`sche_end_time`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=34 DEFAULT CHARSET=utf8 COMMENT='时间计划表';

-- ----------------------------
-- Table structure for t_sensitive_words
-- ----------------------------
DROP TABLE IF EXISTS `t_sensitive_words`;
CREATE TABLE `t_sensitive_words` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `insert_time` datetime DEFAULT NULL COMMENT '插入时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '回收站标记',
  `remarks` varchar(256) DEFAULT NULL COMMENT '备注',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '租户编码',
  `sewo_name` varchar(50) DEFAULT NULL COMMENT '敏感词',
  `sewo_code` varchar(50) DEFAULT NULL COMMENT '敏感词编码',
  `lety_id` bigint(20) DEFAULT NULL COMMENT '词库类别id',
  `extend_1` varchar(50) DEFAULT NULL COMMENT '扩展1',
  `extend_2` varchar(50) DEFAULT NULL COMMENT '扩展2',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='督导-敏感词';

-- ----------------------------
-- Table structure for t_student
-- ----------------------------
DROP TABLE IF EXISTS `t_student`;
CREATE TABLE `t_student` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `user_id` bigint(20) DEFAULT NULL COMMENT '用户ID',
  `stud_registration_status` smallint(6) DEFAULT '1',
  `stud_in_school_status` smallint(6) DEFAULT '1',
  `stud_type` smallint(6) DEFAULT NULL COMMENT '类型 （0：本科；1：研究生)',
  `adcl_id` bigint(20) DEFAULT NULL COMMENT '所属班级id',
  `credits_level` varchar(255) DEFAULT NULL COMMENT '学分级别（三年制、四年制、五年制、七年制）',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_student_user_id` (`user_id`) USING BTREE,
  KEY `idx_adcl_id` (`adcl_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=85749 DEFAULT CHARSET=utf8 COMMENT='学生表';

-- ----------------------------
-- Table structure for t_subject
-- ----------------------------
DROP TABLE IF EXISTS `t_subject`;
CREATE TABLE `t_subject` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `orga_id` bigint(20) DEFAULT NULL COMMENT '开课组织机构ID',
  `acte_id` bigint(20) DEFAULT NULL COMMENT '开课学年学期ID',
  `subj_code` varchar(100) DEFAULT NULL COMMENT '科目编号',
  `subj_name` varchar(100) DEFAULT NULL COMMENT '科目名称',
  `subj_description` text COMMENT '科目简介',
  `subj_img_url` varchar(255) DEFAULT NULL COMMENT '科目图标url',
  `subj_source` smallint(6) DEFAULT '1' COMMENT '科目来源 1 本科生 2 研究生',
  `subject_type_id` bigint(20) DEFAULT NULL COMMENT '课程类型id',
  `subject_nature_id` bigint(20) DEFAULT NULL COMMENT '课程性质id',
  `subject_category_id` bigint(20) DEFAULT NULL COMMENT '课程类别id',
  `total_hours` int(11) DEFAULT '0' COMMENT '总学时',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_subject_orga_id` (`orga_id`) USING BTREE,
  KEY `idx_subject_acte_id` (`acte_id`) USING BTREE,
  KEY `idx_subject_subj_code` (`subj_code`) USING BTREE,
  KEY `idx_subject_subj_name` (`subj_name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=89075 DEFAULT CHARSET=utf8 COMMENT='科目表';

-- ----------------------------
-- Table structure for t_subject_category
-- ----------------------------
DROP TABLE IF EXISTS `t_subject_category`;
CREATE TABLE `t_subject_category` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `category_code` varchar(50) NOT NULL COMMENT '课程类别编码',
  `category_value` varchar(100) NOT NULL COMMENT '课程类别值',
  `sort_order` int(11) DEFAULT '0' COMMENT '排序权重',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `insert_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_category_code` (`category_code`) COMMENT '类别编码唯一约束'
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COMMENT='课程性质表';

-- ----------------------------
-- Table structure for t_subject_nature
-- ----------------------------
DROP TABLE IF EXISTS `t_subject_nature`;
CREATE TABLE `t_subject_nature` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `nature_code` varchar(50) NOT NULL COMMENT '课程性质编码',
  `nature_value` varchar(100) NOT NULL COMMENT '课程性质值',
  `sort_order` int(11) DEFAULT '0' COMMENT '排序权重',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `insert_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_nature_code` (`nature_code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='课程性质表';

-- ----------------------------
-- Table structure for t_subject_organization
-- ----------------------------
DROP TABLE IF EXISTS `t_subject_organization`;
CREATE TABLE `t_subject_organization` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `subj_id` bigint(20) DEFAULT NULL COMMENT '科目id',
  `orga_id` bigint(20) DEFAULT NULL COMMENT '组织机构id',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_subject_organization_subj_id` (`subj_id`) USING BTREE,
  KEY `idx_subject_organization_orga_id` (`orga_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=14863 DEFAULT CHARSET=utf8 COMMENT='科目组织机构中间表';

-- ----------------------------
-- Table structure for t_subject_type
-- ----------------------------
DROP TABLE IF EXISTS `t_subject_type`;
CREATE TABLE `t_subject_type` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `type_code` varchar(50) NOT NULL COMMENT '课程类型编码',
  `type_value` varchar(100) NOT NULL COMMENT '课程类型值',
  `sort_order` int(11) DEFAULT '0' COMMENT '排序权重',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `insert_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_type_code` (`type_code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=110 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='课程类型表';

-- ----------------------------
-- Table structure for t_teacher
-- ----------------------------
DROP TABLE IF EXISTS `t_teacher`;
CREATE TABLE `t_teacher` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `user_id` bigint(20) DEFAULT NULL COMMENT '用户ID',
  `teac_in_service_status` smallint(6) DEFAULT '1',
  `teacher_title` varchar(100) DEFAULT NULL COMMENT '教师职称',
  `employment_start_date` datetime DEFAULT NULL COMMENT '教师入职时间',
  `teacher_title_id` bigint(20) DEFAULT NULL COMMENT '教师职称id',
  `birth_date` datetime DEFAULT NULL COMMENT '老师生日',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_teacher_user_id` (`user_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=23844 DEFAULT CHARSET=utf8 COMMENT='老师表';

-- ----------------------------
-- Table structure for t_teacher_title
-- ----------------------------
DROP TABLE IF EXISTS `t_teacher_title`;
CREATE TABLE `t_teacher_title` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `title_code` varchar(50) NOT NULL COMMENT '教师职称编码',
  `title_value` varchar(100) NOT NULL COMMENT '教师职称值',
  `sort_order` int(11) DEFAULT '0' COMMENT '排序权重',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `insert_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_title_code` (`title_code`) USING BTREE COMMENT '类别编码唯一约束'
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='教师职称表';

-- ----------------------------
-- Table structure for t_teaching_class
-- ----------------------------
DROP TABLE IF EXISTS `t_teaching_class`;
CREATE TABLE `t_teaching_class` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `tecl_code` varchar(100) DEFAULT NULL COMMENT '班级编号',
  `tecl_name` varchar(600) DEFAULT NULL COMMENT '班级名称',
  `acte_id` bigint(20) DEFAULT NULL COMMENT '学年学期ID',
  `subj_id` bigint(20) DEFAULT NULL COMMENT '科目ID',
  `tecl_student_count` int(11) DEFAULT '0',
  `tecl_description` text COMMENT '教学班简介',
  `tecl_img_url` varchar(255) DEFAULT NULL COMMENT '教学班图标url',
  `tecl_notice` text COMMENT '教学班公告',
  `course_no` varchar(200) DEFAULT NULL COMMENT '课程号',
  `total_hours` int(11) NOT NULL DEFAULT '0' COMMENT '总学时',
  `start_week` int(11) DEFAULT NULL COMMENT '教学班开始周',
  `end_week` int(11) DEFAULT NULL COMMENT '教学班结束周',
  `week_detail` varchar(255) DEFAULT NULL COMMENT '教学班周次详情',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_teaching_class_acte_id` (`acte_id`) USING BTREE,
  KEY `idx_teaching_class_subj_id` (`subj_id`) USING BTREE,
  KEY `idx_teaching_class_code` (`tecl_code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=42177 DEFAULT CHARSET=utf8 COMMENT='教学班表';

-- ----------------------------
-- Table structure for t_teaching_class_course_type
-- ----------------------------
DROP TABLE IF EXISTS `t_teaching_class_course_type`;
CREATE TABLE `t_teaching_class_course_type` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT NULL COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(255) DEFAULT NULL COMMENT '所属租户组织编号',
  `tecl_code` varchar(255) DEFAULT NULL COMMENT '班级编号',
  `course_type_code` varchar(255) DEFAULT NULL COMMENT '课程类型编码',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_tecl_code` (`tecl_code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COMMENT='教学班-课程类型关系表';

-- ----------------------------
-- Table structure for t_teaching_class_organization_relation
-- ----------------------------
DROP TABLE IF EXISTS `t_teaching_class_organization_relation`;
CREATE TABLE `t_teaching_class_organization_relation` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `tecl_code` varchar(500) DEFAULT NULL COMMENT '教学班编号',
  `orga_code` varchar(500) DEFAULT NULL COMMENT '院系编号',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tecl_source` varchar(6) DEFAULT NULL COMMENT '教学班来源 1 本科生 2 研究生 ',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_source_tecl_code` (`tecl_code`) USING BTREE,
  KEY `inde1` (`orga_code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=9391 DEFAULT CHARSET=utf8 COMMENT='教学班组织关系表';

-- ----------------------------
-- Table structure for t_teaching_class_re_student
-- ----------------------------
DROP TABLE IF EXISTS `t_teaching_class_re_student`;
CREATE TABLE `t_teaching_class_re_student` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `tecl_code` varchar(5000) DEFAULT NULL,
  `user_code` varchar(255) DEFAULT NULL,
  `insert_time` datetime DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  `recycle_sign` tinyint(2) DEFAULT '0',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='教学班重修人数';

-- ----------------------------
-- Table structure for t_teaching_class_releation_class
-- ----------------------------
DROP TABLE IF EXISTS `t_teaching_class_releation_class`;
CREATE TABLE `t_teaching_class_releation_class` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `tecl_code` varchar(500) NOT NULL COMMENT '教学班编码',
  `class_name` varchar(500) DEFAULT NULL COMMENT '行政班名称',
  `class_code` varchar(500) DEFAULT NULL COMMENT '行政班编码',
  `student_count` int(6) DEFAULT '0' COMMENT '班级人数',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_tecl_code` (`tecl_code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=4737 DEFAULT CHARSET=utf8 COMMENT='教学班与行政班关系表';

-- ----------------------------
-- Table structure for t_teaching_class_student
-- ----------------------------
DROP TABLE IF EXISTS `t_teaching_class_student`;
CREATE TABLE `t_teaching_class_student` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tecl_id` bigint(20) DEFAULT NULL COMMENT '教学班ID',
  `stud_id` bigint(20) DEFAULT NULL COMMENT '学生ID',
  `tcst_data_source` smallint(6) DEFAULT '0' COMMENT '数据来源 0:共享库导入;1:手工添加',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_teaching_class_student_tecl_id` (`tecl_id`) USING BTREE,
  KEY `idx_teaching_class_student_tcst_data_source` (`tcst_data_source`) USING BTREE,
  KEY `idx_teaching_class_student_stud_id_tecl_id` (`stud_id`,`tecl_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=292853 DEFAULT CHARSET=utf8 COMMENT='教学班学生关系表';

-- ----------------------------
-- Table structure for t_teaching_class_student_rebuild
-- ----------------------------
DROP TABLE IF EXISTS `t_teaching_class_student_rebuild`;
CREATE TABLE `t_teaching_class_student_rebuild` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tecl_id` bigint(20) DEFAULT NULL COMMENT '教学班ID',
  `stud_id` bigint(20) DEFAULT NULL COMMENT '学生ID',
  `xk_status` varchar(6) DEFAULT '1' COMMENT '1-初修 2-重修 3-少听 4-免修',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_tecl_student_rebuild_tecl_id` (`tecl_id`) USING BTREE,
  KEY `idx_tecl_student_rebuild_stud_id_tecl_id` (`stud_id`,`tecl_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8 COMMENT='教学班学生关系表(免修重修)';

-- ----------------------------
-- Table structure for t_teaching_class_teacher
-- ----------------------------
DROP TABLE IF EXISTS `t_teaching_class_teacher`;
CREATE TABLE `t_teaching_class_teacher` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `teac_id` bigint(20) DEFAULT NULL COMMENT '授课老师ID',
  `tecl_id` bigint(20) DEFAULT NULL COMMENT '教学班ID',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_teaching_class_teacher_tecl_id` (`tecl_id`) USING BTREE,
  KEY `idx_teaching_class_teacher_teac_id_tecl_id` (`teac_id`,`tecl_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=6647 DEFAULT CHARSET=utf8 COMMENT='教学班班授课老师关系表（可能存在2个以上授课老师给同一个教学班上课的情况）';

-- ----------------------------
-- Table structure for t_tenant
-- ----------------------------
DROP TABLE IF EXISTS `t_tenant`;
CREATE TABLE `t_tenant` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `status` char(1) COLLATE utf8_bin DEFAULT '1',
  `create_dept_name` varchar(50) CHARACTER SET utf8 DEFAULT NULL COMMENT '创建人部门',
  `creator_name` varchar(50) CHARACTER SET utf8 DEFAULT NULL COMMENT '创建人',
  `updater_name` varchar(50) CHARACTER SET utf8 DEFAULT NULL COMMENT '修改人',
  `sign` varchar(50) COLLATE utf8_bin NOT NULL COMMENT '租户标识',
  `name` varchar(50) COLLATE utf8_bin DEFAULT NULL COMMENT '租户名称',
  `is_default` char(1) COLLATE utf8_bin DEFAULT NULL COMMENT '默认租户',
  `sort_index` bigint(10) DEFAULT NULL,
  `address_type` smallint(6) DEFAULT NULL COMMENT '地址类型 0:域名;1,IP',
  `domain_or_ip` varchar(50) COLLATE utf8_bin DEFAULT NULL COMMENT '域名或者IP',
  `remark` varchar(255) COLLATE utf8_bin DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `sign` (`sign`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='租户表';

-- ----------------------------
-- Table structure for t_user
-- ----------------------------
DROP TABLE IF EXISTS `t_user`;
CREATE TABLE `t_user` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `user_id` bigint(20) DEFAULT NULL COMMENT '用户唯一标识',
  `user_code` varchar(50) DEFAULT NULL COMMENT '用户编码:教职工号、学生学号等',
  `user_email` varchar(100) DEFAULT NULL COMMENT '用户邮箱',
  `user_phone_num` varchar(50) DEFAULT NULL COMMENT '用户手机号码',
  `user_identifier_num` varchar(50) DEFAULT NULL COMMENT '用户证件号码',
  `user_status` smallint(6) DEFAULT NULL COMMENT '用户状态:1,启用;0,禁用',
  `user_name` varchar(100) DEFAULT NULL COMMENT '用户姓名',
  `user_gender` smallint(6) DEFAULT NULL COMMENT '用户性别(0:男,1:女)',
  `user_birthday` datetime DEFAULT NULL COMMENT '用户生日',
  `is_tenant_admin` smallint(6) DEFAULT '0' COMMENT '是否租户管理员,默认为0:不是;1,是',
  `begin_date` date DEFAULT NULL COMMENT '有效期开始时间',
  `end_date` date DEFAULT NULL COMMENT '有效期结束时间',
  `wechat_user_id` varchar(100) DEFAULT NULL COMMENT '企业微信id',
  `password` varchar(255) DEFAULT NULL COMMENT '密码',
  `alternate_name` varchar(255) DEFAULT NULL COMMENT '人员别名',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_user_user_id` (`user_id`) USING BTREE,
  KEY `idx_user_user_code` (`user_code`) USING BTREE,
  KEY `idx_user_phone_num` (`user_phone_num`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=200255 DEFAULT CHARSET=utf8 COMMENT='用户表';

-- ----------------------------
-- Table structure for t_user_face_info
-- ----------------------------
DROP TABLE IF EXISTS `t_user_face_info`;
CREATE TABLE `t_user_face_info` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` bigint(20) DEFAULT NULL COMMENT '用户ID',
  `user_code` varchar(50) DEFAULT NULL COMMENT '用户code',
  `user_name` varchar(50) DEFAULT NULL COMMENT '用户姓名',
  `face_image_id` bigint(20) DEFAULT NULL COMMENT '人脸图片文件ID',
  `face_image_path` varchar(500) DEFAULT NULL COMMENT '人脸图片相对路径',
  `face_image_md5` varchar(32) DEFAULT NULL COMMENT '人脸图片MD5值',
  `face_image_resolution` varchar(50) DEFAULT NULL COMMENT '人脸图片分辨率',
  `upload_status` tinyint(4) DEFAULT NULL COMMENT '上传状态（0-失败，1-成功）',
  `face_image_quality` tinyint(4) DEFAULT NULL COMMENT '图片检测状态',
  `upload_msg` varchar(255) DEFAULT NULL COMMENT '上传失败消息',
  `insert_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_user_code_tenant_org_code` (`tenant_org_code`,`user_code`) USING BTREE,
  KEY `idx_recycle_sign` (`recycle_sign`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=127 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='用户人脸信息表';

-- ----------------------------
-- Table structure for t_user_level
-- ----------------------------
DROP TABLE IF EXISTS `t_user_level`;
CREATE TABLE `t_user_level` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `user_code` varchar(255) NOT NULL COMMENT '用户编码:教职工号、学生学号等',
  `role_code` varchar(255) NOT NULL COMMENT '角色编码',
  `user_level` tinyint(1) NOT NULL COMMENT '级别 1-校级 2-院级',
  `recycle_sign` smallint(6) DEFAULT '0' COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `insert_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `app_code` varchar(255) DEFAULT NULL COMMENT '应用标识',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=648 DEFAULT CHARSET=utf8mb4 COMMENT='用户听课级别';

-- ----------------------------
-- Table structure for t_user_role
-- ----------------------------
DROP TABLE IF EXISTS `t_user_role`;
CREATE TABLE `t_user_role` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `insert_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '修改时间',
  `recycle_sign` smallint(6) DEFAULT NULL COMMENT '默认为0:正常;1,删除',
  `tenant_org_code` varchar(50) DEFAULT NULL COMMENT '所属租户组织编号',
  `user_id` varchar(50) DEFAULT NULL COMMENT 'rbac用户id',
  `user_code` varchar(50) DEFAULT NULL COMMENT '用户编码:教职工号、学生学号等',
  `role_id` varchar(50) DEFAULT NULL COMMENT 'rbac角色id',
  `begin_date` date DEFAULT NULL COMMENT '角色有效期开始时间',
  `end_date` date DEFAULT NULL COMMENT '角色有效期结束时间',
  `app_code` varchar(255) DEFAULT NULL COMMENT '应用标识',
  `send_unbinding_time` datetime DEFAULT NULL COMMENT '发送解绑时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_user_role_user_code` (`user_code`) USING BTREE,
  KEY `idx_end_date` (`end_date`),
  KEY `idx_send_unbinding_time` (`send_unbinding_time`)
) ENGINE=InnoDB AUTO_INCREMENT=226532 DEFAULT CHARSET=utf8 COMMENT='用户角色表';

-- ----------------------------
-- View structure for view_teaching_class_student
-- ----------------------------
DROP VIEW IF EXISTS `view_teaching_class_student`;
CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW `view_teaching_class_student` AS select `t_teaching_class_student`.`id` AS `id`,`t_teaching_class_student`.`insert_time` AS `insert_time`,`t_teaching_class_student`.`update_time` AS `update_time`,`t_teaching_class_student`.`recycle_sign` AS `recycle_sign`,`t_teaching_class_student`.`tecl_id` AS `tecl_id`,`t_teaching_class_student`.`stud_id` AS `stud_id`,`t_teaching_class_student`.`tcst_data_source` AS `tcst_data_source` from `t_teaching_class_student`;

-- ----------------------------
-- Procedure structure for add_column_if_not_exists
-- ----------------------------
DROP PROCEDURE IF EXISTS `add_column_if_not_exists`;
delimiter ;;
CREATE PROCEDURE `add_column_if_not_exists`(IN target_table_name  VARCHAR(100),
    IN target_column_name VARCHAR(100),
    IN column_definition  TEXT)
BEGIN
    DECLARE target_database VARCHAR(100);
    DECLARE col_exists INT DEFAULT 0;

    SELECT DATABASE() INTO target_database;

    -- 检查字段是否存在
    SELECT COUNT(*)
    INTO col_exists
    FROM information_schema.COLUMNS
    WHERE table_schema = target_database
      AND table_name = target_table_name
      AND column_name = target_column_name;

    -- 如果字段不存在，则添加
    IF col_exists = 0 THEN
        SET @statement = CONCAT(
            'ALTER TABLE `', target_table_name, '` ',
            'ADD COLUMN `', target_column_name, '` ', column_definition
        );
        PREPARE STMT FROM @statement;
        EXECUTE STMT;
        DEALLOCATE PREPARE STMT;
    END IF;
END
;;
delimiter ;

-- ----------------------------
-- Procedure structure for add_index
-- ----------------------------
DROP PROCEDURE IF EXISTS `add_index`;
delimiter ;;
CREATE PROCEDURE `add_index`(IN target_table_name  VARCHAR(100),
    IN target_column_name VARCHAR(100),  -- 可以是 "col" 或 "col1,col2"
    IN target_index_name  VARCHAR(100))
BEGIN
    DECLARE target_database VARCHAR(100);
    DECLARE idx_exists INT DEFAULT 0;
    DECLARE existing_cols TEXT DEFAULT NULL;
    DECLARE existing_type VARCHAR(20) DEFAULT NULL;

    -- 目标：统一用 BTREE（和你原来一样）
    DECLARE desired_type VARCHAR(20) DEFAULT 'BTREE';

    SELECT DATABASE() INTO target_database;

    -- 1) 判断索引是否存在
    SELECT COUNT(*)
    INTO idx_exists
    FROM information_schema.statistics
    WHERE table_schema = target_database
      AND table_name   = target_table_name
      AND index_name   = target_index_name;

    IF idx_exists = 0 THEN
        -- 不存在：直接创建
        SET @statement = CONCAT(
                'ALTER TABLE `', target_table_name, '` ',
                'ADD INDEX `', target_index_name, '` (', target_column_name, ') USING ', desired_type
                         );
        PREPARE STMT FROM @statement;
        EXECUTE STMT;
        DEALLOCATE PREPARE STMT;

    ELSE
        -- 2) 已存在：取出现有索引列（按顺序拼起来）和 index_type
        SELECT
            GROUP_CONCAT(CONCAT('`', column_name, '`') ORDER BY seq_in_index SEPARATOR ','),
            MAX(index_type)
        INTO existing_cols, existing_type
        FROM information_schema.statistics
        WHERE table_schema = target_database
          AND table_name   = target_table_name
          AND index_name   = target_index_name;

        -- 3) 归一化比较（去空格、去反引号、转小写），避免因为格式不同误判
        IF  LOWER(REPLACE(REPLACE(existing_cols, '`', ''), ' ', '')) <>
            LOWER(REPLACE(REPLACE(target_column_name, '`', ''), ' ', ''))
            OR UPPER(existing_type) <> UPPER(desired_type)
        THEN
            -- 不一致：先删后建
            SET @statement = CONCAT(
                    'ALTER TABLE `', target_table_name, '` ',
                    'DROP INDEX `', target_index_name, '`'
                             );
            PREPARE STMT FROM @statement;
            EXECUTE STMT;
            DEALLOCATE PREPARE STMT;

            SET @statement = CONCAT(
                    'ALTER TABLE `', target_table_name, '` ',
                    'ADD INDEX `', target_index_name, '` (', target_column_name, ') USING ', desired_type
                             );
            PREPARE STMT FROM @statement;
            EXECUTE STMT;
            DEALLOCATE PREPARE STMT;
        END IF;
    END IF;
END
;;
delimiter ;

SET FOREIGN_KEY_CHECKS = 1;
