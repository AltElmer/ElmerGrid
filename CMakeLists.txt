cmake_minimum_required(VERSION 2.8.9)

project(ElmerGrid)

CONFIGURE_FILE(config.h.cmake config.h)

ADD_SUBDIRECTORY(src)
