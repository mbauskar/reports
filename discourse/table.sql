DROP TABLE IF EXISTS `Topics`;
create table `Topics` (
	`id` int NOT NULL AUTO_INCREMENT,
	`slug` varchar(255),
	primary key (`id`)
);

DROP TABLE IF EXISTS `UserActivity`;
create table `UserActivity` (
	`id` int NOT NULL AUTO_INCREMENT,
	`parent` int,
	`created_at` date,
	`user` varchar(255),
	`topic_id` int,
	`post_number` int,
	`title` varchar(255),
	`reply` text,
	primary key (`id`),
	key `parent` (`parent`)
);