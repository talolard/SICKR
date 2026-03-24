data "aws_ssm_parameter" "app_host_ami" {
  name = var.ami_ssm_parameter_name
}

resource "aws_instance" "app_host" {
  ami                         = data.aws_ssm_parameter.app_host_ami.value
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = var.security_group_ids
  iam_instance_profile        = var.instance_profile_name
  associate_public_ip_address = false
  key_name                    = var.ssh_key_name
  user_data = templatefile("${path.module}/templates/user_data.sh.tftpl", {
    artifact_root_dir = var.artifact_root_dir
  })

  instance_initiated_shutdown_behavior = "stop"

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
    instance_metadata_tags      = "enabled"
  }

  root_block_device {
    volume_size           = var.root_volume_size_gib
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-app"
    Component          = "compute"
    Role               = "app-host"
    DataClassification = "internal"
  })
}

resource "aws_eip" "app_host" {
  domain = "vpc"

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-app-eip"
    Component          = "compute"
    Role               = "origin-address"
    DataClassification = "public"
  })
}

resource "aws_eip_association" "app_host" {
  instance_id   = aws_instance.app_host.id
  allocation_id = aws_eip.app_host.id
}

resource "aws_route53_record" "origin" {
  zone_id         = var.hosted_zone_id
  name            = var.origin_hostname
  type            = "A"
  ttl             = 60
  records         = [aws_eip.app_host.public_ip]
  allow_overwrite = true
}
